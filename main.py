import argparse
import sys
from pathlib import Path

from core.sim import Simulator
from core.module_importer import import_agents

def main():

    directory = Path("problem/")
    subdirs = [f.name for f in directory.iterdir() if f.is_dir()]
    #Multi Agents System
    parser = argparse.ArgumentParser(
                                     description='Abstract system of agents with different implementations',
                                     epilog='LEI-PL 2025/26 - 106090,122123',
                                     usage=f'%(prog)s <'+ '/'.join(subdirs) + '> [options]')
    # required arg
    parser.add_argument("problem",choices=subdirs)

    # optional args
    parser.add_argument('-t', '--train', help='training mode', action='store_true')
    parser.add_argument('-v', '--verbose',help="Enable verbose output", action='store_true')

    group = parser.add_mutually_exclusive_group()
    group.add_argument('-s', '--step', default=750, help='step delay (in milliseconds)', type=int, metavar="ms")
    group.add_argument('-l', '--headless', help='run without graphics (mutually exclusive with --step)', action='store_true')

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    args = parser.parse_args()

    # got valid problem chosen
    # process optionals
    if args.train or args.headless or args.train:
        pass

    import_agents()
    sim = Simulator.create(args)
    sim.run()

if __name__ == '__main__':
    main()
