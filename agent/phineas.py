import copy
import random
import pickle # para guardar biblioteca knowledge
import os
from dataclasses import replace

from abstract.agent import AgentStatus
from abstract.nav2d import Navigator2D, CurrLearningEpisode, BaseAttributes
from component.action import Action
from component.direction import Direction
from component.observation import Observation, ObservationType, ObservationBundle
from core.logger import log
from map.position import Position


class Phineas(Navigator2D):
    def __init__(self, problem: str, name: str, properties: dict):
        super().__init__(problem, name, properties)
        # self.char = properties.get("char", "P")

        self.mode = properties.get("mode", "LEARNING").upper()
        _KB_DIR = f"logs/{problem}/kb/"
        os.makedirs(_KB_DIR, exist_ok=True)

        """
            # q-learning attributes
        """
        self.q_table = {}
        self.visit_counts = {}
        self.last_state = None      
        self.last_action = None
        
        if self.mode == "LEARNING":

            self._KB_FILE = f"{_KB_DIR}kb_{self.name}_{self.timestamp}.pkl"

            self.ep = CurrLearningEpisode()

            self.ep.learning_rate = properties.get("learning_rate", 0.1)
            self.ep.discount_factor = properties.get("discount_factor", 0.9)
            self.ep.epsilon = properties.get("epsilon", 0.15)
            self.ep.epsilon_decay = properties.get("epsilon_decay", 0.995)

            agent_config = {
                "learning_rate": self.ep.learning_rate,
                "discount_factor": self.ep.discount_factor,
                "epsilon": self.ep.epsilon,
                "epsilon_decay": self.ep.epsilon_decay,
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


    def start_episode(self):
        """Inicia um novo episódio"""
        if self.mode == "LEARNING":
            self.base_attr = BaseAttributes()
            self.ep = replace(
                CurrLearningEpisode(),
                current=self.ep.current+1,
                learning_rate=self.ep.learning_rate,
                discount_factor=self.ep.discount_factor,
                epsilon=self.ep.epsilon,
                epsilon_decay=self.ep.epsilon_decay)
            # print("Episode", self.ep.current, " current qtable size:", len(self.q_table))
        else:
            super().start_episode()

        self.last_state = None
        self.last_action = None

        # if self.problem == "lighthouse":
        #     self.estimated_objective_position = None #reset posicao estimada lighthouse

        log().vprint(f"{self.name}: Início Episódio {self.ep.current}")

    def end_episode(self, success: bool = False):
        super().end_episode(success)

        # Learning Logger dict
        if self.mode == "LEARNING" and self.learning_logger:
            episode_data = {
                'episode': self.ep.current,
                'total_reward': self.ep.reward,
                'steps': self.ep.steps,
                'success': success,
                'epsilon': self.ep.epsilon,
                'epsilon_decay': self.ep.epsilon_decay,
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

        #Log output do episódio
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

        # epsilon decay for (potential) next episode:
        if self.mode == "LEARNING":
            # epsilon decay was initially 0.995, then experimented with 0.999. It was a bad idea
            # for small grids and an aggressive exploitation: 0.97
            self.ep.epsilon = max(0.05, self.ep.epsilon * self.ep.epsilon_decay)


    def use_sensor(self, post_action: bool = False) -> None:
        super().use_sensor()

        tile = self.curr_observations[ObservationType.LOCATION].payload.tile
        if tile.upper() == "NEST":
            # print("new known nest position:", self._position)
            self.base_attr.known_nest_pos = copy.deepcopy( self.get_pos() )

        return

    def observation(self, obs: Observation):
        if self.base_attr.episode_ended: #se episodio acabou - n se mexe mais
            return

        reward = obs.payload.reward

        if obs.type == ObservationType.TERMINATE:
            """recebeu sinal para terminar episódio"""
            if reward != 0.0:   # not a simulation shutdown
                self.register_reward(reward)
                self._learn(self.last_state)
                direction = self.base_attr.last_attempted_action.params.get("direction")
                self.set_pos( self.get_pos() + direction )
                self.base_attr.pos_history.append(self.get_pos())

            success = self.ep.total_food_delivered > 0 or reward > 0.0

            self.status = AgentStatus.TERMINATED
            self.end_episode(success=success)
            log().print(f"{self.name}: Recebeu TERMINATE. Episódio finalizado.")
            return

        if obs.type == ObservationType.RESPONSE:
            self.register_reward(reward)
            self._learn(self.last_state)

            _last_attempted_action = self.base_attr.last_attempted_action

            if _last_attempted_action:
                if _last_attempted_action.name == "move":
                    direction = _last_attempted_action.params.get("direction")

                    if obs.payload.moved:

                        if direction:
                            self.set_pos( self.get_pos() + direction )
                            self.base_attr.pos_history.append(self.get_pos())

                            # resetstuck counter se se moveu
                            self.base_attr.stuck_counter = 0

                    else:
                        self.base_attr.stuck_counter += 1


    def _choose_q_learning_move(self, valid_moves: list) -> Direction: #choose com q-learning
        state = self._get_state_key()
        # print("curr state:", state)
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

    def _format_obs_for_state(self, obstype: ObservationType):
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
        surr = self._format_obs_for_state(ObservationType.SURROUNDINGS)
        dr = self._format_obs_for_state(ObservationType.DIRECTION)
        loc = self._format_obs_for_state(ObservationType.LOCATION)
        carry = 1 if self.base_attr.carrying else 0
        if carry == 1:  # only possible in foraging
            return f"{surr},{dr},{loc}|{self.last_action}|C:{carry}|{self._get_clipped_relative_pos()}"  # State string

        return f"{surr},{dr},{loc}|{self.last_action}|C:{carry}"  # State string

    def _get_clipped_relative_pos(self):
        if self.base_attr.known_nest_pos is None:
            return None, None
        k = 5
        dx_clipped = max(-k, min(k, self.base_attr.known_nest_pos.x - self.get_pos().x))
        dy_clipped = max(-k, min(k, self.base_attr.known_nest_pos.y - self.get_pos().y))
        return dx_clipped, dy_clipped

    def _learn(self, current_state: str, after_action: bool = False):
        if self.mode != "LEARNING":
            return

        if not self.last_state or not self.last_action:
            return

        old_q = self.q_table.get((self.last_state, self.last_action), 0.0)

        #Recompensa environment
        r_extrinsic = self.ep.last_extrinsic_reward

        #Bónus de curiosidade
        r_exploration = 0.5 / (self.visit_counts.get(current_state, 1))

        total_reward = r_extrinsic + r_exploration #total
        #atualizar tabela cfr Bellman
        max_next_q = float('-inf')
        for move in [Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT]:
            q = self.q_table.get((current_state, str(move)), 0.0)
            max_next_q = max(max_next_q, q)

        new_q = old_q + self.ep.learning_rate * (
                total_reward + self.ep.discount_factor * max_next_q - old_q
        )
        self.q_table[(self.last_state, self.last_action)] = new_q


    def act(self) -> Action:
        if self.base_attr.episode_ended: #se episodio acabou - n se mexe mais
            return self.action.wait()

        #Atualiza sensores
        self.use_sensor(False)

        valid_moves = [Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT]

        final_dir = self._choose_q_learning_move(valid_moves)

        if not final_dir or final_dir not in valid_moves:
            final_dir = random.choice(valid_moves)

        #Guarda estado para aprendizagem
        self.last_state = self._get_state_key()
        self.last_action = str(final_dir)

        # Cria ação
        act = self.action.move(final_dir)
        self.base_attr.last_attempted_action = act

        return act


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
            if self.base_attr.known_nest_pos:
                data['known_nest'] = (self.base_attr.known_nest_pos.x, self.base_attr.known_nest_pos.y)
            else:
                data['known_nest'] = (None, None)

            data['total_food_collected'] = getattr(self, 'total_food_collected', 0)
            data['total_food_delivered'] = getattr(self, 'total_food_delivered', 0)

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
                    self.base_attr.known_nest_pos = Position(*nest_pos)

                # obj_pos = data.get('estimated_objective')
                # if obj_pos:
                #     self.estimated_objective_position = Position(*obj_pos)

            except Exception:
                log().print(f"Error in load_knowledge(): exception reading file {self._KB_FILE}")