import os
import pickle
from pprint import pprint

import matplotlib.pyplot as plt
from core.logger import log

INVALID_EPISODE_COUNT = -1

class GraphLoader:

    def __new__(cls, timestamp):
        obj = super().__new__(cls)
        obj.knowledgefiles = [f for f in os.listdir('.') if os.path.isfile(f) and f"{timestamp}" in f]
        if len(obj.knowledgefiles) == 0:
            log().print(f"Graph: No knowledge files were found with timestamp {timestamp}")
            return None

        obj.num_episodes = cls.confirm_consistent_episode_entries(obj.knowledgefiles)
        if obj.num_episodes == INVALID_EPISODE_COUNT:
            log().print("Graph: Episode lines between agents are not consistent, cannot generate graphs")
            return None
        return obj

    def __init__(self, timestamp):
        log().print("Generating graphs of session", timestamp, "with",self.num_episodes, "episodes:")

        self.agent_line : dict[str, dict[str,list]] = {}

        for path in self.knowledgefiles:

            splits = path.split("_")
            agent_name = "_".join(splits[1:-1])

            try:
                with open(path, "rb") as f:
                    data = pickle.load(f)
                    print(agent_name, "data", data)
                    self.agent_line[agent_name] = {}
                    self.agent_line[agent_name]["rewards"] = data.get('total_rewards')
                    self.agent_line[agent_name]["steps"] = data.get('total_steps')

            except FileNotFoundError:
                print(f"{path}: file not found")
            except Exception as e:
                print(f"{path}: error - {e}")



    def show_graphs(self):
        season_range = range(self.num_episodes + 1)

        fig, ax = plt.subplots(2, 1)

        ax[0].set_title("Rewards")
        ax[1].set_title("Steps")
        ax[0].set_xlabel("Episode")
        ax[1].set_xlabel("Episode")
        ax[0].set_ylabel("Rewards earned")
        ax[1].set_ylabel("Steps Taken")

        for agent, data in self.agent_line.items():
            #print("preparing graphs lines of agent", agent)
            rewards_journey = [0.0]
            rewards_journey.extend(data["rewards"])

            steps_journey = [0.0]
            steps_journey.extend(data["steps"])

            ax[0].plot(season_range, rewards_journey, label=agent)
            ax[1].plot(season_range, steps_journey, label=agent)

        ax[0].legend()
        ax[1].legend()

        plt.tight_layout()
        plt.show()

    @staticmethod
    def confirm_consistent_episode_entries(kbfiles: list[str]):
        num_lines_total = INVALID_EPISODE_COUNT
        for path in kbfiles:
            try:
                with open(path, "rb") as f:
                    data = pickle.load(f)
                    episodes = data.get('current_episode')
                    #print(path, episodes)

                if num_lines_total == INVALID_EPISODE_COUNT:
                    num_lines_total = episodes
                    continue

                if num_lines_total != episodes:
                    return INVALID_EPISODE_COUNT

            except FileNotFoundError:
                print(f"{path}: file not found")
            except Exception as e:
                print(f"{path}: error - {e}")

        return num_lines_total

