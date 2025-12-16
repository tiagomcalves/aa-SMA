import os
import pickle
from pathlib import Path

import matplotlib.pyplot as plt
from core.logger import log

INVALID_EPISODE_COUNT = -1

class GraphLoader:

    def __new__(cls, timestamp, problem):
        obj = super().__new__(cls)
        obj.KB_DIR = f"logs/{problem}/kb/"

        obj.knowledgefiles = [
            f for f in os.listdir(obj.KB_DIR)
            if os.path.isfile(os.path.join(obj.KB_DIR, f))
               and f"{timestamp}" in f
        ]
        log().vprint(obj.knowledgefiles)

        if len(obj.knowledgefiles) == 0:
            log().print(f"Graph: No knowledge files were found with timestamp {timestamp}")
            return None

        obj.num_episodes = cls.confirm_consistent_episode_entries(obj.knowledgefiles, obj.KB_DIR)
        if obj.num_episodes == INVALID_EPISODE_COUNT:
            log().print("Graph: Episode lines between agents are not consistent, cannot generate graphs")
            return None
        return obj

    def __init__(self, timestamp, problem):
        log().print("Generating graphs of session", timestamp, "with",self.num_episodes, "episodes:")

        self.agent_line : dict[str, dict[str,list]] = {}

        for path in self.knowledgefiles:
            path = self.KB_DIR + path
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

        fig, axes = plt.subplots(2, 1, figsize=(12, 7))

        dataset_keys = ["rewards", "steps"]
        season_range = range(self.num_episodes + 1)

        # setting titles and labels to each plot
        titles = ["Rewards earned", "Steps Taken"]
        #x_labels = [""]
        y_labels = ["Rewards", "Steps"]

        for ax, dataset, title, ylabel in zip(axes, dataset_keys, titles, y_labels):
            ax.set_title(title)
            ax.set_xlabel("Episode")
            ax.set_ylabel(ylabel)
            ax.grid(True)

            for agent in self.agent_line:
                journey_from_zero = [0.0]
                journey_from_zero.extend(self.agent_line[agent][dataset])
                ax.plot(season_range, journey_from_zero, label=agent, marker='o')

                for xi, yi in zip(season_range, journey_from_zero):
                    ax.annotate(f"{round(yi):d}", # floating-point decimal removal
                                (xi, yi),
                                textcoords="offset points",
                                xytext=(0, 5),
                                ha='center')

            ax.legend()

        plt.tight_layout()
        plt.show()

    @staticmethod
    def confirm_consistent_episode_entries(kbfiles: list[str], dir):
        num_lines_total = INVALID_EPISODE_COUNT
        for path in kbfiles:
            full_path = os.path.join(dir, path)
            try:
                with open(full_path, "rb") as f:
                    data = pickle.load(f)
                    episodes = data.get('current_episode')
                    #print(path, episodes)

                if num_lines_total == INVALID_EPISODE_COUNT:
                    num_lines_total = episodes
                    continue

                if num_lines_total != episodes:
                    return INVALID_EPISODE_COUNT

            except FileNotFoundError:
                print(f"{full_path}: file not found")
            except Exception as e:
                print(f"{full_path}: error - {e}")

        return num_lines_total

