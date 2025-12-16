# main.py
import argparse
from pathlib import Path
from core.graphs import GraphLoader
from core.logger import Logger


def main():
    directory = Path("problem/")
    subdirs = [f.name for f in directory.iterdir() if f.is_dir()]

    parser = argparse.ArgumentParser(
        description='Draw graphs',
        epilog='LEI-PL 2025/26 - 106090,122123',
        usage=f'%(prog)s problem timestamp',
        add_help=False
    )

    # required arg
    parser.add_argument('problem', choices=subdirs, help='simulation problem')
    parser.add_argument('timestamp', help='timestamp')

    args = parser.parse_args()

    Logger.initialize(verbose=True, problem_name=args.problem)

    graph = GraphLoader(args.timestamp, args.problem)
    if not graph is None:
        while True:
            answer = input("Show graph of simulation? (y/n): ").strip().lower()
            if answer in ("y", "n"):
                break
        if answer == "y":
            graph.show_graphs()
    else:
        print("Graphs are not available")


if __name__ == '__main__':
    main()