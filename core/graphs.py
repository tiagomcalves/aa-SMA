import ast
import os
import pickle
import re
from pathlib import Path
from pprint import pprint

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.colors import LogNorm

from core.logger import log

INVALID_EPISODE_COUNT = -1

class SessionGraphLoader:

    def __new__(cls, timestamp, problem):
        obj = super().__new__(cls)
        obj.problem = problem
        obj.KB_DIR = f"logs/{problem}/report/"

        found_file = [
            f for f in os.listdir(obj.KB_DIR)
            if os.path.isfile(os.path.join(obj.KB_DIR, f))
               and f"{timestamp}" in f
        ]

        if len(found_file) == 0:
            log().print(f"Session Graph: No session file was found with timestamp {timestamp}")
            return None

        if len(found_file) > 1:
            log().print(f"Session Graph: More than one session file was found with timestamp {timestamp}")
            return None

        obj.report_file = found_file[0]

        obj.num_episodes, obj.agent_line = cls.check_agent_cvs_entries_consistency(os.path.join(obj.KB_DIR, obj.report_file))
        if obj.num_episodes == INVALID_EPISODE_COUNT:
            log().print("Session Graph: Lists between agents are not consistent, cannot generate graphs")
            return None
        return obj

    def __init__(self, timestamp, problem):
        log().print("Generating graphs of session", timestamp, "with",self.num_episodes, "episode(s):")

        #report_file : dict[str, dict[str,list]]

    def show_graphs(self):

        fig, axes = plt.subplots(2, 1, figsize=(12, 7))
        fig.suptitle(f"Session Results <{self.problem}>", fontsize=16)

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
    def check_agent_cvs_entries_consistency(report_file: str):
        df = pd.read_csv(report_file)

        # Convert list-like columns
        df['steps'] = df['steps'].apply(ast.literal_eval)
        df['rewards'] = df['rewards'].apply(ast.literal_eval)
        df['successes'] = df['successes'].apply(ast.literal_eval)

        # Use 'name' as dict key
        data = df.set_index('name').to_dict(orient='index')

        dict_lists = []

        for _, agent_data in data.items():
            dict_lists.append([len(v) for v in agent_data.values() if isinstance(v, list)])

        #print("dict lists:", dict_lists)

        for lengths in dict_lists:
            if len(set(lengths)) != 1:
                print("Inconsistent lengths inside an agent:", lengths)
                return INVALID_EPISODE_COUNT, []

        all_first_lengths = [lengths[0] for lengths in dict_lists]

        if len(set(all_first_lengths)) != 1:
            log().vprint("Agents have differing list lengths:", all_first_lengths)
            return INVALID_EPISODE_COUNT, []

        #log().vprint("All agents have consistent list lengths:", all_first_lengths[0])
        return all_first_lengths[0], data


class PickleGraphLoader:

    def __new__(cls, timestamp, problem):
        obj = super().__new__(cls)
        obj.problem = problem
        obj.KB_DIR = f"logs/{problem}/kb/"

        obj.knowledgefiles = [
            f for f in os.listdir(obj.KB_DIR)
            if os.path.isfile(os.path.join(obj.KB_DIR, f))
               and f"{timestamp}" in f
        ]

        if len(obj.knowledgefiles) == 0:
            log().print(f"Graph: No knowledge files were found with timestamp {timestamp}")
            return None

        log().vprint(f"PickeGraph: Found {len(obj.knowledgefiles)} kb file(s)")

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
                    # pprint(f"{agent_name} data, {data}")
                    self.agent_line[agent_name] = {}
                    self.agent_line[agent_name]["rewards"] = data.get('total_rewards')
                    self.agent_line[agent_name]["steps"] = data.get('total_steps')


            except FileNotFoundError:
                print(f"{path}: file not found")
            except Exception as e:
                print(f"{path}: error - {e}")


    def _calculate_rolling_avr(self, data):
        _window = 3
        # print("data len:", len(data))
        moving_avg = np.convolve(
            data,
            np.ones(_window) / _window,
            mode="valid"
        )
        # print("wndw:", _window)
        # print("data input:", data)
        # print("moving avr:", moving_avg)
        return range(_window, self.num_episodes + 1), moving_avg


    def show_graphs(self):

        fig, axes = plt.subplots(2, 1, figsize=(12, 7))
        fig.suptitle(f"Learning Results <{self.problem}>", fontsize=16)

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

                if dataset == "rewards":
                    avr_range, rolling_avr = self._calculate_rolling_avr(self.agent_line[agent][dataset])
                    # print("range:", avr_range)
                    # print("range len:", len(avr_range))
                    # print("rolling arv", rolling_avr)
                    # print("rolling arv len:", len(rolling_avr))
                    ax.plot(avr_range, rolling_avr, label=f"{agent}(rolling avr)", linestyle='-')


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


class HeatmapLoader:

    def __init__(self, timestamp, problem):
        self.KB_DIR = f"logs/{problem}/heatmap/"
        self.timestamp = timestamp
        self.data = None  # This will store a 2D array of values
        self.shape = None  # Shape of the heatmap

    def load_from_dict(self, data: dict[tuple[int,int], int], max_x, max_y ):
        if not data:
            raise ValueError("No data provided.")

        self.shape = (max_x, max_y)
        # print(data)
        # Initialize array
        heatmap = np.zeros(self.shape)
        for (x, y), value in data.items():
            heatmap[y, x] = value

        log().print("Generating heatmap of session", self.timestamp)
        self.data = heatmap

    def draw(self, title: str = "Heatmap", cmap: str = "viridis"):
        if self.data is None:
            raise ValueError("No data loaded.")

        # Mask zeros so empty cells stay light
        masked = np.ma.masked_where(self.data == 0, self.data)

        plt.figure(figsize=(10, 10))
        plt.imshow(
            masked,
            cmap=cmap,
            norm=LogNorm(vmin=1, vmax=masked.max()),
            interpolation="nearest"
        )
        
        plt.colorbar(label="Value (log scale)")
        plt.title(title)
        plt.xlabel("X")
        plt.ylabel("Y")
        plt.show()

    def load_from_file(self):

        found_files = [
            f for f in os.listdir(self.KB_DIR)
            if os.path.isfile(os.path.join(self.KB_DIR, f))
               and f"{self.timestamp}" in f
        ]

        if len(found_files) == 0:
            log().print(f"Heatmap: No session file was found with timestamp {self.timestamp}")
            return None

        if len(found_files) > 1:
            log().print(f"Heatmap: More than one Heatmap file was found with timestamp {self.timestamp}")
            return None

        df = pd.read_csv(os.path.join(self.KB_DIR,found_files[0]))
        heatmap_data = {tuple(xy): count for xy, count in zip(df[['x', 'y']].values, df['count'])}

        match = re.search(r'_(\d+)x(\d+)_', found_files[0])
        if match:
            max_x = int(match.group(1))
            max_y = int(match.group(2))
            # print("max_x:", max_x, "max_y:", max_y)
            self.load_from_dict(heatmap_data, max_x, max_y)
        else:
            print("Could not extract max_x and max_y")

        return None
