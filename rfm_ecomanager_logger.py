from __future__ import print_function
import argparse
import logging
import time
from nanode import Nanode
from manager import Manager

def setup_argparser():
    # Process command line args
    parser = argparse.ArgumentParser(description="Log data from "
                                     "rfm_edf_ecomanager Nanode code.")
    
    parser.add_argument('--edit', dest='edit', action='store_const',
                        const=True, default=False, 
                        help="Pair with new transmitters or edit existing transmitters.")
   
    parser.add_argument('--log', dest='loglevel', type=str, default='DEBUG',
                        help='DEBUG or INFO or WARNING (default: DEBUG)')    

    return parser.parse_args()    


def setup_logger(args):
    numeric_level = getattr(logging, args.loglevel.upper(), None)
    
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: {}'.format(args.loglevel))
    
    logging.basicConfig(filename='rfm_ecomanager_logger.log', level=numeric_level,
                        #format='%(asctime)s level=%(levelname)s: '
                        #'function=%(funcName)s, thread=%(threadName)s'
                        #'\n   %(message)s'
                        format="%(message)s")
    
    logging.debug('MAIN: rfm_ecomanager_logger.py starting up. Unixtime = {:.0f}'
                  .format(time.time()))
    

def main():
    args = setup_argparser()
    
    # args.edit = True # TODO: remove after testing
    
    setup_logger(args)
    
    print("rfm_ecomanager_logger")
    nanode = Nanode(args)
    manager = Manager(nanode, args)
    
    if args.edit:
        manager.run_editing()
    else:
        manager.run_logging()

    
if __name__ == "__main__":
    main()