from __future__ import annotations
from component.observation import ObservationBundle

class State:

    def __init__(self):
        self.pre_sensor_data : Optional[ObservationBundle] = None
        self.action_taken : Optional[Action] = None
        self.reward : float = 0.0
        self.post_sensor_data: Optional[ObservationBundle] = None
        self.mission_concluded : bool = False

    def update_sensor_data(self, after_action: bool = False, bundle: ObservationBundle | None = None) -> None:
        if not after_action:
            self.pre_sensor_data = self.post_sensor_data
            return

        if bundle is None:
            raise ValueError
        self.post_sensor_data = bundle

    def update_reward(self, reward: float):
        self.reward += reward

    def update_action_taken(self, action):
        self.action_taken = action

    def set_final_state(self):
        self.mission_concluded = True

    def save_current_state(self):
        print(self.pre_sensor_data)
        print(self.action_taken)
        print(self.reward)
        print(self.post_sensor_data)
        print(self.mission_concluded)