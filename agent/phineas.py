import random
import pickle # para guardar biblioteca knowledge
import os
from dataclasses import replace
from typing import Optional

from abstract.agent import AgentStatus
from abstract.nav2d import Navigator2D, CurrLearningEpisode, SessionData, BaseAttributes
from abstract.utils.policy import _get_valid_moves, _is_oscillating
from component.action import Action
from component.direction import Direction
from component.observation import Observation, ObservationType, ObservationBundle
from core.logger import log
from map.position import Position


class Phineas(Navigator2D):
    def __init__(self, problem: str, name: str, properties: dict):
        super().__init__(problem, name, properties)
        self.char = properties.get("char", "P")

        self.mode = properties.get("mode", "LEARNING").upper()
        _KB_DIR = f"logs/{problem}/kb/"
        os.makedirs(_KB_DIR, exist_ok=True)

        """
            problem specific attributes
        """
        #estado interno para o problema foraging e q_table
        self.q_table = {}
        self.visit_counts = {}

        #memoria espacial para ter nocao do ninho foraging
        self.known_nest_position: Optional[Position] = self._position
        self.my_estimated_position = self._position

        # Para lighthouse - estimativa de posição do farol
        self.estimated_objective_position: Optional[Position] = None

        """ ------------------------------ """

        self.last_state = None
        self.last_action = None
        self.last_act_moved = False
        
        if self.mode == "LEARNING":

            self._KB_FILE = f"{_KB_DIR}kb_{self.name}_{self.timestamp}.pkl"

            self.ep = CurrLearningEpisode()

            self.ep.learning_rate = properties.get("learning_rate", 0.1)
            self.ep.discount_factor = properties.get("discount_factor", 0.9)
            self.ep.epsilon = properties.get("epsilon", 0.15)

            agent_config = {
                "learning_rate": self.ep.learning_rate,
                "discount_factor": self.ep.discount_factor,
                "epsilon": self.ep.epsilon,
                "problem": problem
            }
            self.learning_logger = log().create_learning_logger(name, self.timestamp, agent_config)
        else:
            stored_kb_timestamp = properties.get('kb', False)
            if not stored_kb_timestamp:
                raise ValueError(f"No KB timestamp argument in {self.name} config")
            
            self._KB_FILE = os.path.join(_KB_DIR, self._get_kb_file(_KB_DIR, stored_kb_timestamp))
        self.load_knowledge()

    # get file with partial timestamp
    def _get_kb_file(self, directory, timestamp):
        knowledge_files = [
                f for f in os.listdir(directory)
                if os.path.isfile(os.path.join(directory, f))
                and f"{timestamp}" in f and self.name in f
            ]
        
        print(knowledge_files)
        if len(knowledge_files) == 0:
            raise ValueError(f"No KB file found  in {self.name} config")
    
        if len(knowledge_files) > 1:
            raise ValueError(f"More than one kb file was found with timestamp {timestamp}: {knowledge_files}")

        return knowledge_files[0]
    # ***
    # GESTÃO DE EPISÓDIOS
    # ***
    def start_episode(self):
        """Inicia um novo episódio"""
        if self.mode == "LEARNING":
            self.base_attributes = BaseAttributes()
            self.ep = replace(
                CurrLearningEpisode(),
                current=self.ep.current+1,
                learning_rate=self.ep.learning_rate,
                discount_factor=self.ep.discount_factor,
                epsilon=self.ep.epsilon)
            print("Episode", self.ep.current, " current qtable size:", len(self.q_table))
        else:
            super().start_episode()

        self.last_state = None
        self.last_action = None
        self.last_act_moved = False
        self._position = Position(0,0)

        if self.problem == "lighthouse":
            self.estimated_objective_position = None #reset posicao estimada lighthouse

        log().vprint(f"{self.name}: Início Episódio {self.ep.current}")

    def end_episode(self, success: bool = False):
        super().end_episode(success)
        #Atualiza epsilon - desvio dos dadoss egundo o tiago alves
        if self.mode == "LEARNING":
            self.ep.epsilon = max(0.05, self.ep.epsilon * 0.999)    #epsilon decay

        # REGISTO NO LOGGER
        if self.mode == "LEARNING" and self.learning_logger:
            episode_data = {
                'episode': self.ep.current,
                'total_reward': self.ep.reward,
                'steps': self.ep.steps,
                'success': success,
                'epsilon': self.ep.epsilon,
                'learning_rate': self.ep.learning_rate,
                'discount_factor': self.ep.discount_factor,
                'q_table_size': len(self.q_table),
                'successful_returns': self.ep.successful_returns,
                'food_collected': self.ep.total_food_collected,
                'food_delivered': self.ep.total_food_delivered,
                'policy': 'Q-learning'
            }
            self.learning_logger.log_episode(episode_data)
            #guardar q-table
            if self.ep.current % 20 == 0:
                self.learning_logger.save_q_table(self.q_table)

        #Log do episódio
        log().print(f"\n{'=' * 50}")
        log().print(f"{self.name}: EPISÓDIO {self.ep.current} FINALIZADO")
        log().print(f"{'=' * 50}")
        log().print(f"Sucesso: {'SIM' if success else 'NÃO'}")
        log().print(f"Recompensa total: {self.ep.reward:.2f}")
        log().print(f"Passos: {self.ep.steps}")

        if self.problem == "foraging":
            log().print(f"Comida apanhada: {self.ep.total_food_collected}")
            log().print(f"Comida entregue: {self.ep.total_food_delivered}")

        if self.mode == "LEARNING":
            log().print(f"epsilon atual: {self.ep.epsilon:.3f}")

        self.save_knowledge()

    # ***
    # SENSOR
    # ***
    def use_sensor(self, post_action: bool = False) -> None:
        super().use_sensor()
        if self.problem == "lighthouse":
            self._estimate_objective_position(self.curr_observations[ObservationType.DIRECTION].payload.direction)

        tile = self.curr_observations[ObservationType.LOCATION].payload.tile
        if tile.upper() == "NEST":
            print("Saving next position")
            self.known_nest_position = self._position

        return

    def _estimate_objective_position(self, direction_vector: tuple[Direction, Direction]):
        x_dir, y_dir = direction_vector #Estimar posicao farol com base na direcao dada
        if not self.estimated_objective_position:
        #Se não temos estimativa inicial, assume que o farol está longe
            large_distance = 20
            self.estimated_objective_position = Position(
                self._position.x + (
                        large_distance * (1 if x_dir == Direction.RIGHT else -1 if x_dir == Direction.LEFT else 0)),
                self._position.y + (
                        large_distance * (1 if y_dir == Direction.DOWN else -1 if y_dir == Direction.UP else 0))
            )
        else: #nova estimativa
            dx = 1 if x_dir == Direction.RIGHT else -1 if x_dir == Direction.LEFT else 0
            dy = 1 if y_dir == Direction.DOWN else -1 if y_dir == Direction.UP else 0
            self.estimated_objective_position = Position(
                self.estimated_objective_position.x + dx,
                self.estimated_objective_position.y + dy
            )

    # ***
    # OBSERVAÇÃO
    # ---------------------------------------------------
    def observation(self, obs: Observation):
        if self.base_attributes.episode_ended: #se episodio acabou - n se mexe mais
            return

        reward = obs.payload.reward

        if obs.type == ObservationType.TERMINATE:
            """recebeu sinal para terminar episódio"""
            if reward != 0.0:   # not a simulation shutdown
                self.register_reward(reward)
                self._learn(self.last_state)
                self.last_act_moved = True
                direction = self.base_attributes.last_attempted_action.params.get("direction")
                self._position = self._position + direction
                self.my_estimated_position = self._position
                self.base_attributes.pos_history.append(self._position)

            success = self.ep.total_food_delivered > 0 or reward > 0.0

            self.status = AgentStatus.TERMINATED
            self.end_episode(success=success)
            log().print(f"{self.name}: Recebeu TERMINATE. Episódio finalizado.")
            return

        if obs.type == ObservationType.RESPONSE:
            self.register_reward(reward)
            self._learn(self.last_state)

            _last_attempted_action = self.base_attributes.last_attempted_action

            if _last_attempted_action:
                if _last_attempted_action.name == "move":
                    direction = _last_attempted_action.params.get("direction")

                    if obs.payload.moved:

                        if direction:
                            self._position = self._position + direction
                            self.my_estimated_position = self._position
                            self.base_attributes.pos_history.append(self._position)

                            # resetstuck counter se se moveu
                            self.base_attributes.stuck_counter = 0
                            self.last_act_moved = True

                    else:
                        self.base_attributes.stuck_counter += 1
                        self.last_act_moved = False


    # ***
    # NAVEGAÇÃO - MÉTODOS AUXILIARES
    # ***
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

        if self.mode == "LEARNING":
            self.visit_counts[state] = self.visit_counts.get(state, 0) + 1

            if self.last_state and self.last_action:
                self._learn(state)

            if random.random() > self.ep.epsilon: #learning epsilon greedy
                return self._choose_best_q_action(state, valid_moves)

            return random.choice(valid_moves)

        return self._choose_best_q_action(state, valid_moves)

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

    def format_obs_for_state(self, obstype: ObservationType):
        if obstype == ObservationType.SURROUNDINGS:
            _cell = self.curr_observations.get(ObservationType.SURROUNDINGS).payload.cells
            return f"({_cell[Direction.UP]},{_cell[Direction.DOWN]},{_cell[Direction.LEFT]},{_cell[Direction.RIGHT]})"

        elif obstype == ObservationType.DIRECTION:
            x_dir, y_dir = self.curr_observations.get(ObservationType.DIRECTION).payload.direction
            return f"({x_dir},{y_dir}"

        elif obstype == ObservationType.LOCATION:
            _tile = self.curr_observations.get(ObservationType.LOCATION).payload.tile.upper()
            return f"<{_tile}>"

        return None

    def _get_state_key(self) -> str: #chave de estado para o q-learning
        surr = self.format_obs_for_state(ObservationType.SURROUNDINGS)
        dir = self.format_obs_for_state(ObservationType.DIRECTION)
        loc = self.format_obs_for_state(ObservationType.LOCATION)
        carry = {1 if self.base_attributes.carrying else 0}
        #moved = {1 if self.last_act_moved else 0}
        return f"{surr},{dir},{loc}|{self._position.x},{self._position.y}|C:{carry}"    # State string

    def _learn(self, current_state: str, after_action: bool = False):
        if not self.last_state or not self.last_action:
            return

        old_q = self.q_table.get((self.last_state, self.last_action), 0.0)

        #Recompensa environment -
        r_extrinsic = self.ep.last_extrinsic_reward

        #Bónus de curiosidade
        r_exploration = 0.5 / (self.visit_counts.get(current_state, 1))

        #bonus proximidade ao lighthouse para esse problema
        r_shaping = 0.0
        # if self.problem == "lighthouse" and self.estimated_objective_position:
        #     diff_x = self.estimated_objective_position.x - self._position.x
        #     diff_y = self.estimated_objective_position.y - self._position.y
        #     move_str = self.last_action  # ex: "(0, 1)" ou "Direction.DOWN"
        #     if "RIGHT" in move_str and diff_x > 0:
        #         r_shaping += 2.0
        #     elif "LEFT" in move_str and diff_x < 0:
        #         r_shaping += 2.0
        #     elif "DOWN" in move_str and diff_y > 0:
        #         r_shaping += 2.0
        #     elif "UP" in move_str and diff_y < 0:
        #         r_shaping += 2.0
        #     else:
        #         r_shaping -= 0.2  # Pequena penalização por se afastar

        total_reward = r_extrinsic + r_exploration + r_shaping #total
        #atualizar tabela cfr Bellman
        max_next_q = float('-inf')
        for move in [Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT]:
            q = self.q_table.get((current_state, str(move)), 0.0)
            max_next_q = max(max_next_q, q)

        new_q = old_q + self.ep.learning_rate * (
                total_reward + self.ep.discount_factor * max_next_q - old_q
        )
        self.q_table[(self.last_state, self.last_action)] = new_q

        # print("qtable entry:", (self.last_state, self.last_action), "=> Old:", old_q, ", New:", new_q)

    # ***
    # ACT
    # ----
    def act(self) -> Action:
        if self.base_attributes.episode_ended: #se episodio acabou - n se mexe mais
            return self.action.wait()

        #Atualiza sensores
        self.use_sensor(False)

        #Obtém movimentos válidos
        # valid_moves = _get_valid_moves(self.curr_observations.get(ObservationType.SURROUNDINGS))
        # if not valid_moves:
        #     act = self.action.wait()    # @tiago: env does not handle wait atm, so nothing happens
        #     _last_attempted_action = act
        #     return act

        valid_moves = [Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT]
        final_dir = None

        #MODO PÂNICO (anti-loop)
        # if _is_oscillating(self.base_attributes.pos_history) or self.base_attributes.stuck_counter > 3:
        #     self.base_attributes.panic_mode = 3
        #     self.base_attributes.stuck_counter = 0

        # if self.base_attributes.panic_mode > 0:
        #     self.base_attributes.panic_mode -= 1
        #     final_dir = random.choice(valid_moves)

        #LÓGICA ESPECÍFICA POR PROBLEMA
        if self.problem == "foraging":
            if self.base_attributes.carrying:
                # Volta ao ninho
                final_dir = self._navigate_towards_target(self.known_nest_position, valid_moves)
            else: #procurar comida com q-learning
                final_dir = self._choose_q_learning_move(valid_moves)

        elif self.problem == "lighthouse": #aproximar-se do objetivo
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
        self.base_attributes.last_attempted_action = act
        return act

    # ****
    # KNOWLEDGE
    def save_knowledge(self):
        if self.mode != "LEARNING":
            return
        
        log().vprint("saving knowledge")
        try:
            # dados comuns aos problemas
            data = {
                'q_table': self.q_table,
                'visit_counts': self.visit_counts,
                'total_rewards': self.session.rewards,
                'total_steps': self.session.steps_per_ep,
                'epsilon': self.ep.epsilon,
                'current_episode': self.ep.current,
                'problem_type': self.problem  # Ajuda a validar se o save é compatível
            }

            #foraging: Ninho e Comida
            if self.known_nest_position:
                data['known_nest'] = (self.known_nest_position.x, self.known_nest_position.y)

            data['total_food_collected'] = getattr(self, 'total_food_collected', 0)
            data['total_food_delivered'] = getattr(self, 'total_food_delivered', 0)

            #lighthouse: Objetivo Estimado
            if self.estimated_objective_position:
                data['estimated_objective'] = (self.estimated_objective_position.x, self.estimated_objective_position.y)

            #escrita no disco
            with open(self._KB_FILE, "wb") as f:
                pickle.dump(data, f)
        except Exception:
            pass

    def load_knowledge(self, file=None):
        if os.path.exists(self._KB_FILE):
            try:
                with open(self._KB_FILE, "rb") as f:
                    data = pickle.load(f)
                #brain
                self.q_table = data.get('q_table', {})
                self.visit_counts = data.get('visit_counts', {})

                #progress
                if self.mode == "LEARNING":
                    self.ep.epsilon = data.get('epsilon', self.ep.epsilon)
                    self.ep.current = data.get('current_episode', 0)
                else:
                    self.ep.current = 0

                #statistics
                self.ep.total_food_collected = data.get('total_food_collected', 0)
                self.ep.total_food_delivered = data.get('total_food_delivered', 0)

                #
                nest_pos = data.get('known_nest')
                if nest_pos:
                    self.known_nest_position = Position(*nest_pos)

                obj_pos = data.get('estimated_objective')
                if obj_pos:
                    self.estimated_objective_position = Position(*obj_pos)

            except Exception:
                log().print(f"Error in load_knowledge(): exception reading file {self._KB_FILE}")