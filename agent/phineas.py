import random
import pickle # para guardar biblioteca knowledge
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

        # Identificação e posição
        self.problem = problem
        self._position = Position(*properties.get("starting_position", (0, 0)))
        self.char = properties.get("char", "P")

        # Parametros reinforcement learning
        self.learning_rate = properties.get("learning_rate", 0.1)
        self.discount_factor = properties.get("discount_factor", 0.9)
        self.epsilon = properties.get("epsilon", 0.15)
        self.mode = properties.get("mode", "LEARNING").upper()

        # Logger para registo
        if self.mode == "LEARNING":
            agent_config = {
                "learning_rate": self.learning_rate,
                "discount_factor": self.discount_factor,
                "epsilon": self.epsilon,
                "problem": problem
            }
            self.learning_logger = log().create_learning_logger(name, agent_config)
        else:
            self.epsilon = 0.0
            self.learning_logger = None

        #historico eps
        self.current_episode = 0
        self.episode_reward = 0.0
        self.episode_steps = 0
        self.episode_rewards = []
        self.episode_successes = []
        self.total_food_collected = 0
        self.total_food_delivered = 0
        self.successful_returns = 0

        #estado interno para o problema foraging e q_table
        self.carrying = False
        self.q_table = {}
        self.visit_counts = {}

        #memoria espacial para ter nocao do ninho foraging
        self.known_nest_position: Optional[Position] = self._position
        self.my_estimated_position = self._position

        # Para lighthouse - estimativa de posição do farol
        self.estimated_objective_position: Optional[Position] = None

        # Sistema anti-loop para nao ficar preso (panic mode e stuck)
        self.pos_history = deque(maxlen=12)
        self.panic_mode = 0
        self.stuck_counter = 0

        self.last_state = None
        self.last_action = None
        self.last_attempted_action = None
        self.last_extrinsic_reward = 0.0

        # Ja terminou episodio?
        self.episode_ended = False

        self.load_knowledge()

    # ---------------------------------------------------
    # GESTÃO DE EPISÓDIOS
    # ---------------------------------------------------
    def start_episode(self):
        """Inicia um novo episódio"""
        self.current_episode += 1
        self.episode_reward = 0.0
        self.episode_steps = 0
        self.last_extrinsic_reward = 0.0
        self.carrying = False
        self.panic_mode = 0
        self.pos_history.clear()
        self.episode_ended = False  #reset flag término

        # Reset posição estimada do objetivo (só para lighthouse)
        if self.problem == "lighthouse":
            self.estimated_objective_position = None

        log().vprint(f"{self.name}: Início Episódio {self.current_episode}")

    def register_reward(self, reward: float):
        #register reward
        self.episode_reward += reward
        self.episode_steps += 1
        self.last_extrinsic_reward = reward

    def end_episode(self, success: bool = False):
        # Verifica se já terminou (evita chamadas duplicadas)
        if self.episode_ended:
            return

        self.episode_ended = True
        self.episode_success = success

        #Guarda no histórico
        self.episode_rewards.append(self.episode_reward)
        self.episode_steps_list = self.episode_steps
        self.episode_successes.append(1 if success else 0)

        #Atualiza epsilon (apenas em modo LEARNING) - desvio dos dadoss egundo o tiago alves
        if self.mode == "LEARNING":
            self.epsilon = max(0.01, self.epsilon * 0.995)

        # REGISTO NO LOGGER (apenas para Q-learning em modo LEARNING)
        if self.mode == "LEARNING" and self.learning_logger:
            episode_data = {
                'episode': self.current_episode,
                'total_reward': self.episode_reward,
                'steps': self.episode_steps,
                'success': success,
                'epsilon': self.epsilon,
                'learning_rate': self.learning_rate,
                'discount_factor': self.discount_factor,
                'q_table_size': len(self.q_table),
                'successful_returns': self.successful_returns,
                'food_collected': self.total_food_collected,
                'food_delivered': self.total_food_delivered,
                'policy': 'Q-learning'
            }

            self.learning_logger.log_episode(episode_data)

            # Salva Q-table periodicamente
            if self.current_episode % 20 == 0:
                self.learning_logger.save_q_table(self.q_table)

        # Log do episódio
        log().print(f"\n{'=' * 50}")
        log().print(f"{self.name}: EPISÓDIO {self.current_episode} FINALIZADO")
        log().print(f"{'=' * 50}")
        log().print(f"Sucesso: {'SIM' if success else 'NÃO'}")
        log().print(f"Recompensa total: {self.episode_reward:.2f}")
        log().print(f"Passos: {self.episode_steps}")

        if self.problem == "foraging":
            log().print(f"Comida apanhada: {self.total_food_collected}")
            log().print(f"Comida entregue: {self.total_food_delivered}")

        if self.mode == "LEARNING":
            log().print(f"🎲 ε atual: {self.epsilon:.3f}")

        # Guarda conhecimento
        self.save_knowledge()

    # ---------------------------------------------------
    # SENSORES
    # ---------------------------------------------------
    def use_sensor(self) -> Observation:
        obs = self._sensor.get_info(self)
        self.state.update_sensor_data(True, obs)

        if obs.surroundings:
            self.curr_observations[ObservationType.SURROUNDINGS] = obs.surroundings

        if obs.directions:
            self.curr_observations[ObservationType.DIRECTION] = obs.directions
            # Para lighthouse, estima posição do farol
            if self.problem == "lighthouse" and obs.directions.payload:
                self._estimate_objective_position(obs.directions.payload.direction)

        if obs.location:
            self.curr_observations[ObservationType.LOCATION] = obs.location
            tile = getattr(obs.location.payload, 'tile_name', "").upper()
            if tile == "NEST":
                self.known_nest_position = self._position

        return obs

    def _estimate_objective_position(self, direction_vector: tuple[Direction, Direction]):
        #Estimar posicao farol com base na direcao dada
        x_dir, y_dir = direction_vector

        #Se não temos estimativa inicial, assume que o farol está longe
        if not self.estimated_objective_position:
            #Assume que o farol está a uma distância "grande" na direção indicada
            large_distance = 20
            self.estimated_objective_position = Position(
                self._position.x + (
                        large_distance * (1 if x_dir == Direction.RIGHT else -1 if x_dir == Direction.LEFT else 0)),
                self._position.y + (
                        large_distance * (1 if y_dir == Direction.DOWN else -1 if y_dir == Direction.UP else 0))
            )
        else:
            #Refina estimativa baseada na nova direção
            dx = 1 if x_dir == Direction.RIGHT else -1 if x_dir == Direction.LEFT else 0
            dy = 1 if y_dir == Direction.DOWN else -1 if y_dir == Direction.UP else 0

            self.estimated_objective_position = Position(
                self.estimated_objective_position.x + dx,
                self.estimated_objective_position.y + dy
            )

    def _update_sensor(self):
        self.curr_observations.clear()
        return self.use_sensor()

    # ---------------------------------------------------
    # OBSERVAÇÃO
    # ---------------------------------------------------
    def observation(self, obs: Observation):
        """Processa observações do ambiente"""

        if self.episode_ended:
            return

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

                        # resetstuck counter se se moveu
                        self.stuck_counter = 0

                    #det automática de pickup/drop (para foraging)
                    if self.problem == "foraging" and reward >= 40.0:
                        if not self.carrying:
                            self.carrying = True
                            self.total_food_collected += 1
                            log().vprint(f"{self.name}: Apanhou comida!")
                        else:
                            self.carrying = False
                            self.total_food_delivered += 1
                            self.successful_returns += 1
                            log().vprint(f"{self.name}: Entregou comida no ninho!")

                elif self.last_attempted_action.name == "pick":
                    if self.problem == "foraging":
                        self.carrying = True
                        self.total_food_collected += 1
                    elif self.problem == "lighthouse":
                        # No lighthouse, pick é o objetivo - NÃO chama end_episode aqui
                        # O ambiente enviará Observation.TERMINATE
                        log().vprint(f"{self.name}: Chegou ao objetivo")

                elif self.last_attempted_action.name == "drop":
                    if self.problem == "foraging":
                        self.carrying = False
                        self.total_food_delivered += 1
                        self.successful_returns += 1
                        log().vprint(f"{self.name}: Depositou no ninho!")

        elif obs.type == ObservationType.DENIED:
            self.stuck_counter += 1
            self.register_reward(-0.1)

        elif obs.type == ObservationType.TERMINATE:
            """CRÍTICO: Recebeu sinal para terminar episódio"""
            reward = obs.payload.reward if obs.payload else 0.0
            self.register_reward(reward)

            # Determina sucesso baseado no problema
            if self.problem == "foraging":
                success = self.total_food_delivered > 0
            elif self.problem == "lighthouse":
                success = True
            else:
                success = False

            # Muda status para TERMINATED
            self.status = AgentStatus.TERMINATED
            self.end_episode(success=success)

            log().print(f"🏁 {self.name}: Recebeu TERMINATE. Episódio finalizado.")

    # ---------------------------------------------------
    # NAVEGAÇÃO - MÉTODOS AUXILIARES
    # ---------------------------------------------------
    def _is_oscillating(self) -> bool:
        if len(self.pos_history) < 6:
            return False
        unique_pos = set(list(self.pos_history)[-6:])
        return len(unique_pos) <= 2

    def _get_valid_moves(self) -> list[Direction]: #movimentos validos
        obs_surr = self.curr_observations.get(ObservationType.SURROUNDINGS)
        valid_moves = []
        if obs_surr:
            bad_tiles = ["#", "WALL", "OBSTACLE", "X", "W"]
            cells = obs_surr.payload.cells
            for d, c in cells.items():
                if d != Direction.NONE and str(c).upper().strip() not in bad_tiles:
                    valid_moves.append(d)
        else:
            valid_moves = [Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT]
        return valid_moves

    def _navigate_towards_target(self, target: Optional[Position], valid_moves: list) -> Direction:
        #andar para alvo
        if not target or not valid_moves:
            return random.choice(valid_moves) if valid_moves else None
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

    def _choose_q_learning_move(self, valid_moves: list) -> Direction: #choose com q-learning
        state = self._get_state_key()
        self.visit_counts[state] = self.visit_counts.get(state, 0) + 1
        if self.mode == "LEARNING" and self.last_state and self.last_action:
            self._learn(state)
        if self.mode == "TEST": #caso esteja a testar - escolhe sempre a melhor acao
            return self._choose_best_q_action(state, valid_moves)
        else:
            if random.random() > self.epsilon: #learning epsilon greedy
                return self._choose_best_q_action(state, valid_moves)
            else:
                return random.choice(valid_moves)
    def _choose_best_q_action(self, state: str, valid_moves: list) -> Direction: #escolher acao com melhor q
        best_q = float('-inf')
        best_actions = []
        for move in valid_moves:
            q = self.q_table.get((state, str(move)), 0.0)
            if q > best_q:
                best_q = q
                best_actions = [move]
            elif q == best_q:
                best_actions.append(move)
        return random.choice(best_actions) if best_actions else random.choice(valid_moves)
    def _get_state_key(self) -> str: #chave de estado para o q-learning
        if self.problem == "foraging":
            return f"C:{1 if self.carrying else 0}|Pos:{self._position.x},{self._position.y}"
        elif self.problem == "lighthouse":
            # Inclui direção do farol no estado
            obs_dir = self.curr_observations.get(ObservationType.DIRECTION)
            if obs_dir and obs_dir.payload:
                x_dir, y_dir = obs_dir.payload.direction
                return f"Dir:{x_dir},{y_dir}|Pos:{self._position.x},{self._position.y}"
            else:
                return f"Dir:None|Pos:{self._position.x},{self._position.y}"
        else:
            return f"Pos:{self._position.x},{self._position.y}"
    def _learn(self, current_state: str):#atualizar q-table
        if not self.last_state or not self.last_action:
            return
        old_q = self.q_table.get((self.last_state, self.last_action), 0.0)
        # Recompensa intrinseca*************************************************
        exploration_bonus = 0.5 / (self.visit_counts.get(current_state, 0) + 1)
        total_reward = self.last_extrinsic_reward + exploration_bonus
        #melhor Q do próximo estado
        max_next_q = 0.0
        for move in [Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT]:
            q = self.q_table.get((current_state, str(move)), 0.0)
            max_next_q = max(max_next_q, q)
        #atualização Q-learning
        new_q = old_q + self.learning_rate * (
                total_reward + self.discount_factor * max_next_q - old_q
        )
        self.q_table[(self.last_state, self.last_action)] = new_q

    # ---------------------------------------------------
    # ACT
    # ---------------------------------------------------
    def act(self) -> Action:
        if self.episode_ended: #se episodio acabou - n se mexe mais
            return self.action.wait()
        #Atualiza sensores
        self._update_sensor()

        # Ações imediatas - pick ou drop
        obs_loc = self.curr_observations.get(ObservationType.LOCATION)
        if obs_loc:
            tile = getattr(obs_loc.payload, 'tile_name', "").upper()
            if self.problem == "foraging":
                if not self.carrying and tile in ["FOOD", "RESOURCE"]:
                    act = self.action.pick()
                    self.last_attempted_action = act
                    return act
                if self.carrying and tile == "NEST":
                    act = self.action.drop()
                    self.last_attempted_action = act
                    return act
            elif self.problem == "lighthouse" and tile in ["OBJECTIVE", "O", "@"]:
                act = self.action.pick()
                self.last_attempted_action = act
                return act
        #Obtém movimentos válidos
        valid_moves = self._get_valid_moves()
        if not valid_moves:
            act = self.action.wait()
            self.last_attempted_action = act
            return act
        final_dir = None

        #MODO PÂNICO (anti-loop)
        if self._is_oscillating() or self.stuck_counter > 3:
            self.panic_mode = 3
            self.stuck_counter = 0

        if self.panic_mode > 0:
            self.panic_mode -= 1
            final_dir = random.choice(valid_moves)

        #LÓGICA ESPECÍFICA POR PROBLEMA
        elif self.problem == "foraging":
            if self.carrying:
                # Volta ao ninho
                final_dir = self._navigate_towards_target(self.known_nest_position, valid_moves)
            else: #procurar comida com q-learning
                final_dir = self._choose_q_learning_move(valid_moves)

        elif self.problem == "lighthouse": #aproximar-se do objetivo
            # Opção A: Usa direção do sensor se disponível
            obs_dir = self.curr_observations.get(ObservationType.DIRECTION)
            if obs_dir and obs_dir.payload:
                x_dir, y_dir = obs_dir.payload.direction
                preferred_dirs = []
                # PRIORIDADE: Movimento que vai na direção do farol
                if x_dir in valid_moves:
                    preferred_dirs.append(x_dir)
                if y_dir in valid_moves:
                    preferred_dirs.append(y_dir)
                if preferred_dirs:
                    # Escolhe uma das direções preferidas
                    final_dir = random.choice(preferred_dirs)
                else:
                    # Se não pode ir nas direções preferidas, tenta aproximar-se
                    if self.estimated_objective_position:
                        final_dir = self._navigate_towards_target(self.estimated_objective_position, valid_moves)
                    else:
                        # Fallback: Q-learning
                        final_dir = self._choose_q_learning_move(valid_moves)
            else:
                # Sem direção do sensor
                if self.estimated_objective_position:
                    # Usa estimativa de posição
                    final_dir = self._navigate_towards_target(self.estimated_objective_position, valid_moves)
                else:
                    # Fallback: Q-learning
                    final_dir = self._choose_q_learning_move(valid_moves)

        else:
            #outros problemas: Q-learning genérico
            final_dir = self._choose_q_learning_move(valid_moves)

        #Final verification
        if not final_dir or final_dir not in valid_moves:
            final_dir = random.choice(valid_moves)

        #Guarda estado para aprendizagem
        if self.mode == "LEARNING":
            self.last_state = self._get_state_key()
            self.last_action = str(final_dir)

        # Cria ação
        act = self.action.move(final_dir)
        self.last_attempted_action = act
        return act

    # ---------------------------------------------------
    # PERSISTÊNCIA
    # ---------------------------------------------------
    def save_knowledge(self):
        try:
            data = {
                'q_table': self.q_table,
                'visit_counts': self.visit_counts,
                'known_nest': (self.known_nest_position.x, self.known_nest_position.y)
                if self.known_nest_position else None,
                'estimated_objective': (self.estimated_objective_position.x, self.estimated_objective_position.y)
                if self.estimated_objective_position else None,
                'total_rewards': self.episode_rewards,
                'epsilon': self.epsilon,
                'current_episode': self.current_episode,
                'total_food_delivered': self.total_food_delivered
            }
            with open(f"knowledge_{self.name}.pkl", "wb") as f:
                pickle.dump(data, f)
        except Exception as e:
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

                nest_pos = data.get('known_nest')
                if nest_pos:
                    self.known_nest_position = Position(*nest_pos)

                obj_pos = data.get('estimated_objective')
                if obj_pos and self.problem == "lighthouse":
                    self.estimated_objective_position = Position(*obj_pos)

            except Exception:
                pass