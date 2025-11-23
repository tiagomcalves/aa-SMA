from typing import Union

from typing_extensions import final

from component.action import Action

@final
class Scheduler:

    def __init__(self):
        self._step = 0
        self._queue = {}
        self._last_queue_key = 5

    def step(self):
        self._step += 1

    def curr_step(self) -> int:
        return self._step

    def current_task(self) -> Union[Action, None]:
        return self._queue.get(self._step)

    def schedule(self, action: Action):
        if self._step > self._last_queue_key:
            self._last_queue_key = self._step + 1

        while self._queue.get(self._last_queue_key):
            self._last_queue_key += 1

        self._queue[self._last_queue_key] = action