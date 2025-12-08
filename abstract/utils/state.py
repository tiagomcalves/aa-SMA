from __future__ import annotations
from component.observation import ObservationType
from abstract.utils.action_builder import ActionBuilder
from component.observation import ObservationBundle
import time

class State:

    def __init__(self, problem_name: str, agent_name: str):
        self.problem_name = problem_name
        self.agent_name = agent_name
        self.pre_sensor_data : ObservationBundle = ObservationBundle()
        self.action_taken = ActionBuilder.wait
        self.reward : float = 0.0
        self.post_sensor_data : ObservationBundle = ObservationBundle()
        self.mission_concluded : bool = False
        file_dir = f"logs/{problem_name}/{agent_name}_{format(int(time.time()))}.txt"
        self.file = open(file_dir, "a", buffering=1)

    def update_sensor_data(self, after_action: bool = False, bundle: ObservationBundle | None = None) -> None:
        if bundle is None:
            if not after_action:
                self.pre_sensor_data = self.post_sensor_data
                return

            self.post_sensor_data = self.pre_sensor_data
            return

        if not after_action:
            self.pre_sensor_data = bundle
            return

        self.post_sensor_data = bundle

    def update_reward(self, reward: float):
        self.reward += reward

    def update_action_taken(self, action):
        self.action_taken = action

    def set_final_state(self):
        self.mission_concluded = True

    def log_state(self):
        pre_surroundings = f"{self.pre_sensor_data.unpack(ObservationType.SURROUNDINGS)}"
        pre_direction = f"{self.pre_sensor_data.unpack(ObservationType.DIRECTION)}"
        pre_location = f"{self.pre_sensor_data.unpack(ObservationType.LOCATION)}"

        action = f"{self.action_taken.name}:{self.action_taken.params}"

        #reward

        post_surroundings = f"{self.post_sensor_data.unpack(ObservationType.SURROUNDINGS)}"
        post_direction = f"{self.post_sensor_data.unpack(ObservationType.DIRECTION)}"
        post_location = f"{self.post_sensor_data.unpack(ObservationType.LOCATION)}"

        #mission concluded?

        self.file.write(f"{pre_surroundings},{pre_direction},{pre_location},{action},{self.reward},{post_surroundings},{post_direction},{post_location},{self.mission_concluded}\n")

        if self.mission_concluded:
            self.file.close()