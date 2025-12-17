# main.py
import argparse
import sys
import time
from pathlib import Path

from core.graphs import PickleGraphLoader, SessionGraphLoader
from core.renderer.r_handle import Renderer
from core.sim import Simulator
from core.module_importer import import_agents
from core.logger import Logger


def main():
    timestamp = time.time()
    directory = Path("problem/")
    subdirs = [f.name for f in directory.iterdir() if f.is_dir()]

    parser = argparse.ArgumentParser(
        description='Abstract multi-agents system with different implementations',
        epilog='LEI-PL 2025/26 - 106090,122123',
        usage=f'%(prog)s problem [options]',
        add_help=False
    )

    # required arg
    parser.add_argument('problem', choices=subdirs, help='simulation problem')

    # optional args
    parser.add_argument('-a', '--autostart', help='automatically start simulation', action='store_true')
    parser.add_argument('-r', '--renderer', help='renders board in separate process', action='store_true')
    parser.add_argument('-l', '--headless', help='run without renderer (mutually exclusive with --renderer)',
                        action='store_true')
    parser.add_argument('-s', '--step', default=750, help='set a step delay (in milliseconds) (default is 750ms)',
                        type=int, metavar="ms")
    parser.add_argument('-e', '--episodes', default=5, help='set number of episodes per simulation',
                        type=int, metavar="episodes")
    parser.add_argument('-t', '--test', help='testing mode', action='store_true')
    parser.add_argument('-v', '--verbose', help="enable verbose output", action='store_true')

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    args = parser.parse_args()

    # Validações
    if args.headless and args.renderer:
        raise AttributeError("Error: --headless and --renderer are mutually exclusive")

    # if args.test:
    #     raise AttributeError("Error: --learn and --test are mutually exclusive")

    # Inicializa logger COM NOME DO PROBLEMA
    Logger.initialize(verbose=args.verbose, problem_name=args.problem)  # CORRIGIDO

    import_agents()
    sim = Simulator.create(args, timestamp)

    if not args.autostart:
        input("Press <Enter> to start the simulation...")

    sim.run()

    if not args.test:
        pickle_graph = PickleGraphLoader(timestamp, args.problem)
        if not pickle_graph is None:
            while True:
                answer = input("Show learning graph of simulation? (y/n): ").strip().lower()
                if answer in ("y", "n"):
                    break
            if answer == "y":
                pickle_graph.show_graphs()
        else:
            print("Learning graphs are not available")

    session_graph = SessionGraphLoader(timestamp, args.problem)
    if not session_graph is None:
        while True:
            answer = input("Show session graph of simulation? (y/n): ").strip().lower()
            if answer in ("y", "n"):
                break
        if answer == "y":
            session_graph.show_graphs()
    else:
        print("Session graphs are not available")

if __name__ == '__main__':
    main()