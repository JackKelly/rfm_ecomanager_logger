from __future__ import print_function
from nanode import Nanode
from manager import Manager
import argparse

def setup_argparser():
    # Process command line args
    parser = argparse.ArgumentParser(description="Log data from "
                                     "rfm_edf_ecomanager Nanode code.")
    
    parser.add_argument('--promiscuous', dest='promiscuous', action='store_const',
                        const=True, default=False, 
                        help="Pair with all unknown transmitters.")

    parser.add_argument('--edit', dest='edit', action='store_const',
                        const=True, default=False, 
                        help="Edit saved radio IDs.")

    return parser.parse_args()    


def main():
    args = setup_argparser()
    
    print("rfm_ecomanager_logger")
    nanode = Nanode(args)
    manager = Manager(nanode, args)
    manager.run()

    
if __name__ == "__main__":
    main()