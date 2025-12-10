from typing import Union
from typing_extensions import final

from component.action import Action

@final
class Scheduler:

    def __init__(self, max_steps: int, max_episodes=1):
        if max_episodes < 1 or max_steps < 1:
            raise ValueError("Scheduler() max_steps and max_episodes must be >=1")

        self._step = 0
        self._episode = 0
        self._max_steps = max_steps
        self._max_episodes = max_episodes
        self._queue = {}
        self._last_queue_key = 5

    def step(self):
        self._queue.pop(self._step, None)
        self._step += 1

    def curr_step(self) -> int:
        return self._step

    def current_task(self) -> Union[Action, None]:
        return self._queue.get(self._step)

    def out_of_steps(self) -> bool:
        return self._step == self._max_steps

    def schedule(self, action: Action):
        if self._step > self._last_queue_key:
            self._last_queue_key = self._step + 1

        while self._queue.get(self._last_queue_key):
            self._last_queue_key += 1

        self._queue[self._last_queue_key] = action

    def next_episode(self):
        self._queue.clear()
        self._step = 0
        self._episode += 1

    def curr_episode(self) -> int:
        return self._episode

    def out_of_episode(self) -> bool:
        return self._episode == self._max_episodes

    def is_last_episode(self) -> bool:
        return self._episode == self._max_episodes-1