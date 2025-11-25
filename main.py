import argparse
import sys
from pathlib import Path

from core.sim import Simulator
from core.module_importer import import_agents
import core.logger
from core.logger import Logger

def main():

    directory = Path("problem/")
    subdirs = [f.name for f in directory.iterdir() if f.is_dir()]
    
    parser = argparse.ArgumentParser(description='Abstract multi-agents system with different implementations',
                                     epilog='LEI-PL 2025/26 - 106090,122123',
                                     usage=f'%(prog)s problem [options]',
                                     add_help=False)
    
    # required arg
    parser.add_argument('problem',choices=subdirs, help='simulation problem')

    mutex_group = parser.add_mutually_exclusive_group()

    # optional args
    parser.add_argument('-a', '--autostart', help='automatically start simulation', action='store_true')
    mutex_group.add_argument('-l', '--headless', help='run without renderer (mutually exclusive with --step)', action='store_true')
    mutex_group.add_argument('-s', '--step', default=750, help='set a step delay (in milliseconds) (default is 750ms)', nargs=1, type=int, metavar="ms")
    parser.add_argument('-t', '--train', help='training mode', action='store_true')
    parser.add_argument('-v', '--verbose',help="enable verbose output", action='store_true')


    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)
    
    args = parser.parse_args()

    # got valid problem chosen, process optionals

    Logger.initialize(args.verbose)

    if args.train or args.headless:
        pass

    import_agents()
    sim = Simulator.create(args)

    if not args.autostart:
        input("Press <Enter> to start the simulation...")

    sim.run()

if __name__ == '__main__':
    main()
