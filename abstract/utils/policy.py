from abc import ABC, abstractmethod
import random

from typing import Optional
from abstract.nav2d import BaseAttributes
from core.logger import log
from abstract.utils.action_builder import ActionBuilder
from component.observation import Observation, ObservationType
from component.direction import Direction
from map.entity import TileType


class Policy(ABC):
    @abstractmethod
    def act(self, name, curr_observations: dict[ObservationType, Observation], attr: BaseAttributes, action:ActionBuilder):
        pass


class LighthousePolicy(Policy):
    def act(self, name, curr_observations: dict[ObservationType, Observation], attr: BaseAttributes, action:ActionBuilder):
        obs_loc = curr_observations.get(ObservationType.LOCATION)
        if obs_loc:
            tile = getattr(obs_loc.payload, 'tile', "EMPTY").upper()

            if tile in ["OBJECTIVE"]:
                act = action.pick()
                attr.last_attempted_action = act
                return act

        obs_surr = curr_observations.get(ObservationType.SURROUNDINGS)

        # check valid moves

        valid_moves = _get_valid_moves(obs_surr)

        if not valid_moves:
            act = action.wait()
            attr.last_attempted_action = act
            return act

        # detecao de stuck
        _panic_mode = attr.panic_mode
        if _is_stuck(attr.stuck_counter, attr.pos_history) or _panic_mode > 0:
            if _panic_mode == 0:
                _panic_mode = 3  # 3 movs fica em panico
            else:
                _panic_mode -= 1
            # No modo pânico, movimento totalmente aleatório
            final_dir = _choose_random_direction(valid_moves, attr.last_attempted_action, avoid_recent=False)

            act = action.move(final_dir)
            attr.last_attempted_action = act
            return act

        # specific lighthouse

        obs_dir = curr_observations.get(ObservationType.DIRECTION)
        final_dir = None
        if obs_dir:
            dx, dy = obs_dir.payload.direction
            candidates = []
            if dx in valid_moves:
                candidates.append(dx)
            if dy in valid_moves:
                candidates.append(dy)
            if candidates:
                final_dir = random.choice(candidates)
                # seguir direcao farol

        if not final_dir:
            final_dir = _choose_random_direction(valid_moves, attr.last_attempted_action)

        if final_dir not in valid_moves:
            log().vprint(f"{self.name}: Direção inválida, corrigindo...")
            final_dir = _choose_random_direction(valid_moves, attr.last_attempted_action)

            # Cria ação
        act = action.move(final_dir)
        attr.last_attempted_action = act
        return act


class ForagingPolicy(Policy):
    def act(self, name, curr_observations: dict[ObservationType, Observation], attr: BaseAttributes, action:ActionBuilder):

        obs_loc = curr_observations.get(ObservationType.LOCATION)
        if obs_loc:
            tile = getattr(obs_loc.payload, 'tile', "EMPTY").upper()

            if not attr.carrying and tile in ["FOOD", "RESOURCE", "F"]:
                act = action.pick()
                attr.last_attempted_action = act  # apanhar food
                return act

                # Se está no ninho E está carregando
            if attr.carrying and tile == "NEST":
                act = action.drop()
                attr.last_attempted_action = act  # entregar
                return act

        # check valid moves
        obs_surr = curr_observations.get(ObservationType.SURROUNDINGS)

        valid_moves = _get_valid_moves(obs_surr)

        if not valid_moves:
            act = action.wait()
            attr.last_attempted_action = act
            return act

        # detecao de stuck
        _panic_mode = attr.panic_mode
        if _is_stuck(attr.stuck_counter, attr.pos_history) or _panic_mode > 0:
            if _panic_mode == 0:
                _panic_mode = 3  # 3 movs fica em panico
            else:
                _panic_mode -= 1
            # No modo pânico, movimento totalmente aleatório
            final_dir = _choose_random_direction(valid_moves, attr.last_attempted_action, avoid_recent=False)

            act = action.move(final_dir)
            attr.last_attempted_action = act
            return act

        # FORAGING: COMPORTAMENTO ALEATÓRIO
        if attr.carrying:  # se tiver a carregar
            # Primeiro verifica se vê ninho diretamente
            nest_dir = _scan_for_nest(obs_surr, valid_moves)
            if nest_dir:
                final_dir = nest_dir
            else:
                # Se não vê ninho, movimento aleatório
                final_dir = _choose_random_direction(valid_moves, attr.last_attempted_action, avoid_recent=False)
        # Se não está carregando, comportamento de busca aleatória
        else:
            # Verifica se vê comida nas redondezas
            food_dir = _scan_for_food(obs_surr, valid_moves)
            if food_dir:
                final_dir = food_dir  # vai em direcao a comida
            else:
                # COMPORTAMENTO ALEATÓRIO TOTAL
                final_dir = _navigate_randomly_with_momentum(valid_moves, attr.last_attempted_action, attr.wander_tendency)
                log().vprint(f"{name}: Exploração aleatória: {final_dir}")

        if final_dir not in valid_moves:
            log().vprint(f"{name}: Direção inválida, corrigindo...")
            final_dir = _choose_random_direction(valid_moves, attr.last_attempted_action)

        #Cria ação
        act = action.move(final_dir)
        attr.last_attempted_action = act
        return act


class MazePolicy(Policy):
    def act(self, name, curr_observations: dict[ObservationType, Observation], attr: BaseAttributes, action:ActionBuilder):
        pass



#    registering problem string to policy class

POLICY_REGISTRY = {
    "lighthouse": LighthousePolicy(),
    "foraging": ForagingPolicy(),
    "maze": MazePolicy()
}



"""
    Auxiliary functions
"""

# general movement checks

def _get_valid_moves(surroundings: Observation) -> list:
    """Obtém movimentos válidos (não colisiveis)"""
    valid_moves = []

    if surroundings:
        bad_tiles = []  #deactivated
        cells = surroundings.payload.cells
        for direction, content in cells.items():
            is_wall = content in bad_tiles
            if not is_wall:
                valid_moves.append(direction)
    else:
        valid_moves = [Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT]

    return valid_moves


def _is_stuck(stuck_counter, pos_history) -> bool: #ta preso ou em loop
    if stuck_counter >= 3:
        return True

    if len(pos_history) >= 6:
        # Verifica se está repetindo as últimas posições
        recent = pos_history[-6:]
        if len(set(recent)) <= 2:
            return True

    return False


def _choose_random_direction(valid_moves: list, last_attempt_action, avoid_recent: bool = True) -> Direction:
    #random diretion
    if not valid_moves:
        return None

    # Se temos histórico de ações recentes, evita voltar para trás imediatamente
    if avoid_recent and last_attempt_action and len(valid_moves) > 1:
        if last_attempt_action.name == "move":
            last_dir = last_attempt_action.params.get("direction")
            if last_dir:
                opposite = last_dir.opposite() if hasattr(last_dir, 'opposite') else None
                # Remove direção oposta das opções (evita ir e voltar)
                filtered = [d for d in valid_moves if d != opposite]
                if filtered:
                    return random.choice(filtered)

    # Escolha totalmente aleatória
    return random.choice(valid_moves)


def _navigate_randomly_with_momentum(valid_moves: list, last_attempt_action, wander_tendency) -> Optional[Direction]:
    # Caminha aleatoriamente com inercia
    if not valid_moves:
        return None

    # Se o último movimento foi aceito e ainda é válido, tem chance de continuar
    if (last_attempt_action and
            last_attempt_action.name == "move" and
            random.random() < wander_tendency):

        last_dir = last_attempt_action.params.get("direction")
        if last_dir and last_dir in valid_moves:
            return last_dir

    # Caso contrário, escolhe aleatoriamente
    return _choose_random_direction(valid_moves, last_attempt_action)


def _is_oscillating(pos_history) -> bool:
    if len(pos_history) < 6:
        return False
    unique_pos = set(list(pos_history)[-6:])
    return len(unique_pos) <= 2

# foraging-specific auxiliary functions

def _scan_for_food(surroundings, valid_moves: list) -> Optional[Direction]:  # verifica comida redondezas
    if surroundings:
        for direction, content in surroundings.payload.cells.items():
            if direction not in valid_moves:
                continue

            content_upper = str(content).upper().strip()
            if content_upper in ["FOOD", "F", "RESOURCE"]:  # viu comida
                return direction
    return None


def _scan_for_nest(surroundings, valid_moves: list) -> Optional[Direction]:
    """Verifica se vê ninho nas redondezas (quando carregando)"""
    if surroundings:
        for direction, content in surroundings.payload.cells.items():
            if direction not in valid_moves:
                continue

            content_upper = str(content).upper().strip()
            if content_upper in ["NEST", "N"]:  # viu ninho
                return direction
    return None
