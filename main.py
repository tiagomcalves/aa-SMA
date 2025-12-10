# main.py
import argparse
import sys
import time
from pathlib import Path

from core.renderer.r_handle import Renderer
from core.sim import Simulator
from core.module_importer import import_agents
from core.logger import Logger


def main():
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
    parser.add_argument('-rl', '--learn', help='training mode', type=int, metavar="episodes")
    parser.add_argument('-t', '--test', help='testing mode', action='store_true')
    parser.add_argument('-v', '--verbose', help="enable verbose output", action='store_true')

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    args = parser.parse_args()

    # Validações
    if args.headless and args.renderer:
        raise AttributeError("Error: --headless and --renderer are mutually exclusive")

    if args.learn and args.test:
        raise AttributeError("Error: --learn and --test are mutually exclusive")

    # Inicializa logger COM NOME DO PROBLEMA
    Logger.initialize(verbose=args.verbose, problem_name=args.problem)  # CORRIGIDO

    import_agents()
    sim = Simulator.create(args)

    if not args.autostart:
        input("Press <Enter> to start the simulation...")

    sim.run()


if __name__ == '__main__':
    main()