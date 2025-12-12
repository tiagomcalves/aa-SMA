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
            return None

        obj.num_episodes = cls.confirm_consistent_episode_entries(obj.knowledgefiles)
        if obj.num_episodes == INVALID_EPISODE_COUNT:
            log().print("Graph: Episode lines between agents are not consistent, cannot generate graphs")
            return None
        return obj

    def __init__(self, timestamp):
        print("Number of episodes to graph:", self.num_episodes)

        self.agent_line : dict[str, list] = {}

        for path in self.knowledgefiles:

            splits = path.split("_")
            agent_name = "_".join(splits[1:-1])

            try:
                with open(path, "rb") as f:
                    data = pickle.load(f)
                    self.agent_line[agent_name] = data.get('total_rewards')

            except FileNotFoundError:
                print(f"{path}: file not found")
            except Exception as e:
                print(f"{path}: error - {e}")

        pprint(self.agent_line)

    def show_graphs(self):
        season_range = range(self.num_episodes)
        for agent, rewards in self.agent_line.items():
            plt.plot(season_range, rewards, label=agent)
        plt.legend()
        plt.show()


    @staticmethod
    def confirm_consistent_episode_entries(kbfiles: list[str]):
        num_lines_total = INVALID_EPISODE_COUNT
        for path in kbfiles:
            try:
                with open(path, "rb") as f:
                    data = pickle.load(f)
                    episodes = data.get('current_episode')
                    print(path, episodes)

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

