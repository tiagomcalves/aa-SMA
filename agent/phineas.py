import random
import pickle
import os
from typing import Optional
from collections import deque

from abstract.agent import AgentStatus
from abstract.nav2d import Navigator2D
from component.action import Action
from component.direction import Direction
from component.observation import Observation, ObservationType
from core.logger import log
from map.position import Position


class Phineas(Navigator2D):
    def __init__(self, problem: str, name: str, properties: dict):
        super().__init__(problem, name, properties)

        # 1. IDENTIFICAÇÃO E POSIÇÃO
        self.problem = problem
        self._position = Position(*properties.get("starting_position", (0, 0)))
        self.char = properties.get("char", "P")

        # 2. PARÂMETROS RL
        self.learning_rate = properties.get("learning_rate", 0.1)
        self.discount_factor = properties.get("discount_factor", 0.9)
        self.epsilon = properties.get("epsilon", 0.15)
        self.mode = properties.get("mode", "LEARNING").upper()

        # 3. LOGGER E ESTATÍSTICAS
        if self.mode == "LEARNING":
            agent_config = {
                "learning_rate": self.learning_rate,
                "discount_factor": self.discount_factor,
                "epsilon": self.epsilon,
                "problem": problem
            }
            self.learning_logger = log().create_learning_logger(name, agent_config)
            log().print(f"🧠 {self.name}: MODO APRENDIZAGEM ATIVADO")
        else:
            self.epsilon = 0.0
            self.learning_logger = None
            log().print(f"🧪 {self.name}: MODO TESTE ATIVADO")

        # Histórico de Episódios
        self.current_episode = 0
        self.episode_reward = 0.0
        self.episode_steps = 0
        self.episode_rewards = []
        self.episode_successes = []
        self.total_food_collected = 0
        self.total_food_delivered = 0
        self.successful_returns = 0

        # 4. ESTADO INTERNO
        self.carrying = False
        self.q_table = {}
        self.visit_counts = {}

        # Memória Espacial e Estimativa
        # Assume que nasce no ninho
        self.known_nest_position: Optional[Position] = self._position
        self.my_estimated_position = self._position

        # 5. SISTEMA ANTI-LOOP
        self.pos_history = deque(maxlen=12)
        self.panic_mode = 0
        self.stuck_counter = 0

        self.last_state = None
        self.last_action = None
        self.last_attempted_action = None
        self.last_extrinsic_reward = 0.0

        self.load_knowledge()

    # ---------------------------------------------------
    # GESTÃO DE EPISÓDIOS
    # ---------------------------------------------------
    def start_episode(self):
        self.current_episode += 1
        self.episode_reward = 0.0
        self.episode_steps = 0
        self.last_extrinsic_reward = 0.0
        self.carrying = False
        self.panic_mode = 0
        self.pos_history.clear()

        log().vprint(f"🚀 {self.name}: Início Episódio {self.current_episode}")

    def register_reward(self, reward: float):
        self.episode_reward += reward
        self.episode_steps += 1
        self.last_extrinsic_reward = reward

    def end_episode(self, success: bool = False):
        self.episode_rewards.append(self.episode_reward)
        self.episode_successes.append(1 if success else 0)

        if self.mode == "LEARNING" and self.learning_logger:
            data = {
                'episode': self.current_episode,
                'total_reward': self.episode_reward,
                'steps': self.episode_steps,
                'success': success,
                'epsilon': self.epsilon,
                'food_collected': self.total_food_collected,
                'food_delivered': self.total_food_delivered
            }
            self.learning_logger.log_episode(data)

            self.epsilon = max(0.01, self.epsilon * 0.995)

            if self.current_episode % 20 == 0:
                self.save_knowledge()

        log().print(f"📊 Fim Ep.{self.current_episode} | Reward: {self.episode_reward:.1f} | Sucesso: {success}")
        # --- LOG FINAL DETALHADO (O QUE PEDISTE) ---
        log().print(f"\n{'=' * 50}")
        log().print(f"🏁 FIM DO EPISÓDIO {self.current_episode}")
        log().print(f"{'=' * 50}")
        log().print(f"🤖 Agente: {self.name}")
        log().print(f"✅ Sucesso: {'SIM' if success else 'NÃO'}")
        log().print(f"💰 Recompensa Total: {self.episode_reward:.2f}")
        log().print(f"👣 Passos Deste Episódio: {self.episode_steps}")
        log().print(f"🍎 Comida Coletada (Total): {self.total_food_collected}")
        log().print(f"🏠 Entregas no Ninho (Total): {self.total_food_delivered}")

    # ---------------------------------------------------
    # SENSORES
    # ---------------------------------------------------
    def use_sensor(self) -> Observation:
        obs = self._sensor.get_info(self)
        self.state.update_sensor_data(True, obs)

        if obs.surroundings:
            self.curr_observations[ObservationType.SURROUNDINGS] = obs.surroundings
            self._scan_surroundings(obs.surroundings.payload.cells)

        if obs.directions:
            self.curr_observations[ObservationType.DIRECTION] = obs.directions

        if obs.location:
            self.curr_observations[ObservationType.LOCATION] = obs.location
            tile = getattr(obs.location.payload, 'tile_name', "").upper()
            if tile == "NEST":
                self.known_nest_position = self._position

        return obs

    def _scan_surroundings(self, cells: dict):
        for direction, content in cells.items():
            if direction == Direction.NONE: continue
            content = str(content).upper().strip()
            if content in ["NEST", "N"]:
                self.known_nest_position = self._position + direction

    def _update_sensor(self):
        self.curr_observations.clear()
        return self.use_sensor()

    # ---------------------------------------------------
    # OBSERVAÇÃO
    # ---------------------------------------------------
    def observation(self, obs: Observation):
        if obs.type == ObservationType.ACCEPTED:
            reward = obs.payload.reward
            self.register_reward(reward)

            if self.last_attempted_action:
                if self.last_attempted_action.name == "move":
                    direction = self.last_attempted_action.params.get("direction")
                    if direction:
                        self._position = self._position + direction
                        self.my_estimated_position = self._position
                        self.pos_history.append(self._position)

                    if reward >= 40.0:
                        if not self.carrying:
                            self.carrying = True
                            self.total_food_collected += 1
                            log().print(f"✅ {self.name}: Apanhei comida!")
                        else:
                            self.carrying = False
                            self.total_food_delivered += 1
                            self.successful_returns += 1
                            self.end_episode(success=True)

                elif self.last_attempted_action.name == "pick":
                    self.carrying = True
                    self.total_food_collected += 1

                elif self.last_attempted_action.name == "drop":
                    self.carrying = False
                    self.total_food_delivered += 1
                    self.end_episode(success=True)

        elif obs.type == ObservationType.DENIED:
            self.stuck_counter += 1
            self.register_reward(-0.1)

        elif obs.type == ObservationType.TERMINATE:
            self.register_reward(obs.payload.reward)
            self.status = AgentStatus.TERMINATED
            self.end_episode(success=True)
            self.save_knowledge()

    # ---------------------------------------------------
    # NAVEGAÇÃO
    # ---------------------------------------------------
    def _is_oscillating(self) -> bool:
        if len(self.pos_history) < 6: return False
        unique_pos = set(list(self.pos_history)[-6:])
        return len(unique_pos) <= 2

    def _navigate_euclidean(self, target: Position, valid_moves: list) -> Direction:
        best_move = None
        min_dist_sq = float('inf')

        for move in valid_moves:
            next_pos = self._position + move
            diff = target - next_pos
            dist_sq = (diff.x ** 2) + (diff.y ** 2)

            if dist_sq < min_dist_sq:
                min_dist_sq = dist_sq
                best_move = move
            elif dist_sq == min_dist_sq and random.random() < 0.5:
                best_move = move

        return best_move if best_move else random.choice(valid_moves)

    def _get_valid_moves(self, obs_surr) -> list[Direction]:
        if not obs_surr: return [Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT]

        bad_tiles = ["#", "WALL", "OBSTACLE", "X", "W"]
        valid = []
        for d, c in obs_surr.payload.cells.items():
            if d != Direction.NONE and str(c).upper().strip() not in bad_tiles:
                valid.append(d)
        return valid

    def _scan_adjacent_food(self, valid_moves: list) -> Optional[Direction]:
        """ VÊ COMIDA NAS CASAS VIZINHAS? VAI LÁ! """
        obs_surr = self.curr_observations.get(ObservationType.SURROUNDINGS)
        if obs_surr:
            for d, c in obs_surr.payload.cells.items():
                if d in valid_moves:
                    if str(c).upper().strip() in ["FOOD", "RESOURCE", "F"]:
                        log().print(f"👀 {self.name}: Vi comida em {d}! Indo pegar.")
                        return d
        return None

    # ---------------------------------------------------
    # ACT (CÉREBRO)
    # ---------------------------------------------------
    def act(self) -> Action:
        self._update_sensor()

        # 1. AÇÕES IMEDIATAS (Pick/Drop)
        obs_loc = self.curr_observations.get(ObservationType.LOCATION)
        if obs_loc:
            tile = getattr(obs_loc.payload, 'tile_name', "").upper()
            if not self.carrying and tile in ["FOOD", "RESOURCE"]:
                act = self.action.pick();
                self.last_attempted_action = act;
                return act
            if self.carrying and tile == "NEST":
                act = self.action.drop();
                self.last_attempted_action = act;
                return act

        # 2. FILTRO DE PAREDES
        obs_surr = self.curr_observations.get(ObservationType.SURROUNDINGS)
        valid_moves = self._get_valid_moves(obs_surr)

        if not valid_moves:
            log().print(f"⚠️ {self.name}: ENCURRALADO!")
            act = self.action.wait();
            self.last_attempted_action = act;
            return act

        final_dir = None

        # 3. MODO PÂNICO
        if self._is_oscillating() or self.stuck_counter > 3:
            self.panic_mode = 5
            self.stuck_counter = 0

        if self.panic_mode > 0:
            self.panic_mode -= 1
            final_dir = random.choice(valid_moves)

        # 4. MODO RETORNO (CARRYING)
        elif self.carrying:
            target = self.known_nest_position
            if not target:
                # Usa sensor hack ou assume topo-esquerdo
                if ObservationType.DIRECTION in self.curr_observations:
                    d = self.curr_observations[ObservationType.DIRECTION].payload.direction
                    target = Position(self._position.x + (15 * d[0]), self._position.y + (15 * d[1]))
                else:
                    target = Position(1, 1)

            final_dir = self._navigate_euclidean(target, valid_moves)

        # 5. MODO EXPLORAÇÃO
        else:
            # A. VISÃO DE ÁGUIA: Vê comida ao lado?
            food_dir = self._scan_adjacent_food(valid_moves)

            if food_dir:
                final_dir = food_dir
            else:
                # B. Q-LEARNING
                state = self._get_state_key()
                self.visit_counts[state] = self.visit_counts.get(state, 0) + 1

                if self.mode == "LEARNING": self._learn(state, valid_moves)

                if self.mode == "TEST" or random.random() > self.epsilon:
                    # Exploit
                    max_q = float('-inf')
                    best_opts = []
                    for m in valid_moves:
                        q = self.q_table.get((state, str(m)), 0.0)
                        if q > max_q:
                            max_q = q; best_opts = [m]
                        elif q == max_q:
                            best_opts.append(m)
                    final_dir = random.choice(best_opts) if best_opts else random.choice(valid_moves)
                else:
                    # Explore
                    final_dir = random.choice(valid_moves)

        if final_dir not in valid_moves: final_dir = random.choice(valid_moves)

        self.last_state = self._get_state_key() if not self.carrying else None
        self.last_action = str(final_dir)
        act = self.action.move(final_dir)
        self.last_attempted_action = act
        return act

    # ---------------------------------------------------
    # APRENDIZAGEM
    # ---------------------------------------------------
    def _get_state_key(self) -> str:
        return f"C:{1 if self.carrying else 0}|Pos:{self._position}"

    def _learn(self, state, valid_moves):
        if not self.last_state or not self.last_action: return
        old_q = self.q_table.get((self.last_state, self.last_action), 0.0)

        bonus = 0.5 / (self.visit_counts.get(state, 0) + 1)
        total_r = self.last_extrinsic_reward + bonus

        max_next = float('-inf')
        for m in [Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT]:
            q = self.q_table.get((state, str(m)), 0.0)
            if q > max_next: max_next = q
        if max_next == float('-inf'): max_next = 0.0

        new_q = old_q + self.learning_rate * (total_r + (self.discount_factor * max_next) - old_q)
        self.q_table[(self.last_state, self.last_action)] = new_q

    # ---------------------------------------------------
    # PERSISTÊNCIA
    # ---------------------------------------------------
    def save_knowledge(self):
        try:
            data = {
                'q_table': self.q_table,
                'visit_counts': self.visit_counts,
                'known_nest': (self.known_nest_position.x,
                               self.known_nest_position.y) if self.known_nest_position else None,
                'total_rewards': self.episode_rewards,
                'epsilon': self.epsilon,
                'current_episode': self.current_episode
            }
            with open(f"knowledge_{self.name}.pkl", "wb") as f:
                pickle.dump(data, f)
        except Exception:
            pass

    def load_knowledge(self):
        filename = f"knowledge_{self.name}.pkl"
        if os.path.exists(filename):
            try:
                with open(filename, "rb") as f:
                    data = pickle.load(f)
                self.q_table = data.get('q_table', {})
                self.visit_counts = data.get('visit_counts', {})
                self.epsilon = data.get('epsilon', self.epsilon)
                self.current_episode = data.get('current_episode', 0)
                if data.get('known_nest'):
                    self.known_nest_position = Position(*data['known_nest'])
            except Exception:
                pass