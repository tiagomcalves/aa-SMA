from abc import ABC, abstractmethod
import random

from typing import Optional
from abstract.nav2d import BaseAttributes
from core.logger import log
from abstract.utils.action_builder import ActionBuilder
from component.observation import Observation, ObservationType
from component.direction import Direction
from map.entity import TileType
from map.position import Position


class Policy(ABC):
    @abstractmethod
    def act(self, name, curr_observations: dict[ObservationType, Observation], attr: BaseAttributes, action:ActionBuilder):
        pass


class LighthousePolicy(Policy):
    def act(self, name, curr_observations: dict[ObservationType, Observation], attr: BaseAttributes, action:ActionBuilder):

        obs_surr = curr_observations.get(ObservationType.SURROUNDINGS)

        # check valid moves
        valid_moves = _get_valid_moves(obs_surr)

        if not valid_moves:
            act = action.wait()
            attr.last_attempted_action = act
            return act

        # lighthouse specific

        dx, dy = curr_observations.get(ObservationType.DIRECTION).payload.direction
        final_dir = None

        if attr.follow_wall:
            if _is_obstacle_passed( (dx, dy), attr.saved_directions):
                attr.follow_wall = False

        if not attr.follow_wall:
            attr.saved_directions = (dx, dy)
            candidates = []
            if dx in valid_moves:
                candidates.append(dx)
            if dy in valid_moves:
                candidates.append(dy)
            if candidates:
                final_dir = random.choice(candidates)
                # seguir direcao farol
        else:
            final_dir = _follow_wall(valid_moves)

        if not final_dir:
            attr.follow_wall = True
            final_dir = _follow_wall(valid_moves)

            # Cria ação
        act = action.move(final_dir)
        attr.last_attempted_action = act
        return act


class ForagingPolicy(Policy):
    def act(self, name, curr_observations: dict[ObservationType, Observation], attr: BaseAttributes, action:ActionBuilder):
        obs_surr = curr_observations.get(ObservationType.SURROUNDINGS)

        valid_moves = _get_valid_moves(obs_surr)
        if not valid_moves:
            act = action.wait()
            attr.last_attempted_action = act
            return act

        final_dir = None

        if attr.carrying:
            if attr.known_nest_pos is None:
                nest_in_surr = _scan_for_nest(obs_surr, valid_moves)
                if nest_in_surr:
                    final_dir = nest_in_surr
                else:
                    final_dir = _choose_random_direction(valid_moves, attr.last_attempted_action, avoid_recent=False)
            else:
                dx, dy = _convert_vec_to_direction(attr.pos, attr.known_nest_pos)

                if attr.follow_wall:
                    if _is_obstacle_passed( (dx, dy), attr.saved_directions):
                        attr.follow_wall = False

                if not attr.follow_wall:
                    attr.saved_directions = (dx, dy)
                    candidates = []
                    if dx in valid_moves:
                        candidates.append(dx)
                    if dy in valid_moves:
                        candidates.append(dy)
                    if candidates:
                        final_dir = random.choice(candidates)
                else:
                    final_dir = _follow_wall(valid_moves)

                if not final_dir:
                    attr.follow_wall = True
                    final_dir = _follow_wall(valid_moves)
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
    cells = surroundings.payload.cells

    if TileType.NONE in cells.values():
        return [Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT]

    valid_moves = []
    bad_tiles = [ TileType.BOUNDARIES, TileType.COLLIDEABLE]
    for direction, content in cells.items():
        if content not in bad_tiles:
            valid_moves.append(direction)

    return valid_moves

def _is_obstacle_passed(new_directions: tuple[Direction,Direction], saved_directions: tuple[Direction,Direction]):
    if saved_directions[0] is not None and new_directions[0] != saved_directions[0] \
        or saved_directions[1] is not None and new_directions[1] != saved_directions[1]:
        return True
    return False

def _convert_vec_to_direction(from_pos: Position, to_pos: Position):
    fX = to_pos.x - from_pos.x
    fY = to_pos.y - from_pos.y
    fX_direction_axis : Direction
    fY_direction_axis : Direction
    if fX > 0:
        fX_direction_axis = Direction.RIGHT
    elif fX < 0:
        fX_direction_axis = Direction.LEFT
    else:
        fX_direction_axis = Direction.NONE

    if fY > 0:
        fY_direction_axis = Direction.DOWN
    elif fY < 0:
        fY_direction_axis = Direction.UP
    else:
        fY_direction_axis = Direction.NONE

    return fX_direction_axis, fY_direction_axis

def _follow_wall(valid_moves):
    #follow right-handed
    next_direction = None
    if Direction.RIGHT in valid_moves:
        next_direction = Direction.RIGHT
    elif next_direction is None and Direction.UP in valid_moves:
        next_direction = Direction.UP
    elif next_direction is None and Direction.LEFT in valid_moves:
        next_direction = Direction.LEFT
    elif next_direction is None and Direction.DOWN in valid_moves:
        next_direction = Direction.DOWN
    return next_direction

def _is_stuck(stuck_counter, pos_history) -> bool: #ta preso ou em loop
    if stuck_counter >= 3:
        return True
    if len(pos_history) >= 6:
        # Verifica se está repetindo as últimas posições
        recent = pos_history[-6:]
        if len(set(recent)) <= 2:
            return True
    return False

def _choose_random_direction(valid_moves: list, last_attempt_action, avoid_recent: bool = True) -> Optional[Direction]:
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
    for direction, content in surroundings.payload.cells.items():
        if direction not in valid_moves:
            continue

        if content in [TileType.PICKABLE]:
            return direction
    return None


def _scan_for_nest(surroundings, valid_moves: list) -> Optional[Direction]:
    """Verifica se vê ninho nas redondezas (quando carregando)"""
    for direction, content in surroundings.payload.cells.items():
        if direction not in valid_moves:
            continue

        if content in [ TileType.NEST ]:
            return direction
    return None