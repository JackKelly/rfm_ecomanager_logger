#!/usr/bin/python
from __future__ import print_function
import argparse
import logging
import time
import os
import sys
import sighandler
from nanode import Nanode
from manager import Manager


def setup_argparser():
    # Process command line _args
    parser = argparse.ArgumentParser(description="Log data from "
                                     "rfm_edf_ecomanager Nanode code.")
    
    parser.add_argument('--edit', dest='edit', action='store_const',
                        const=True, default=False, 
                        help="Pair with new transmitters or edit existing transmitters.")
   
    parser.add_argument('--log', dest='loglevel', type=str, default='DEBUG',
                        help='DEBUG or INFO or WARNING (default: DEBUG)')  
    
    parser.add_argument('--data-directory', dest='data_directory', type=str
                        ,default=os.path.dirname(os.path.realpath(__file__)) + '/data/'
                        ,help='directory for storing data (default: ./data/)')
    
    parser.add_argument('--port', dest='port', type=str
                        ,default='/dev/ttyUSB0'
                        ,help='serial port (default: /dev/ttyUSB0)')    
    
    return parser.parse_args()


def pre_process_data_directory(args):

    # append trailing slash to data_directory if necessary
    if args.data_directory[-1] != "/":
        args.data_directory += "/"
    
    # if directory doesn't exist then create it
    if not os.path.isdir(args.data_directory[:-1]):
        if os.path.exists(args.data_directory[:-1]):
            logging.critical("The path specified as the data directory '{}' "
                          "is not a directory but is a file. Please try again."
                          .format(args.data_directory[:-1]))
            sys.exit(1)
        os.makedirs(args.data_directory)

    return args


def setup_logger(args):
    numeric_level = getattr(logging, args.loglevel.upper(), None)
    
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: {}'.format(args.loglevel))
    
    logfile = os.path.dirname(os.path.realpath(__file__)) + "/rfm_ecomanager_logger.log" 
    logging.basicConfig(filename=logfile, level=numeric_level, 
                        format="%(message)s")
    
    logging.debug('MAIN: rfm_ecomanager_logger.py starting up. Unixtime = {:.0f}'
                  .format(time.time()))


def main():    
    args = setup_argparser()
    
    setup_logger(args)
    
    args = pre_process_data_directory(args)
    
    print("rfm_ecomanager_logger")
    
    try:
        with Nanode(args) as nanode:
            manager = Manager(nanode, args)
            
            if args.edit:
                manager.run_editing()
            else:
                # register SIGINT and SIGTERM handler
                sig_handler = sighandler.SigHandler()
                sig_handler.add_objects_to_stop([nanode, manager])
                manager.run_logging()
    except:
        logging.exception("")
        raise

    print("\nshutdown")
    logging.shutdown()
    
    
if __name__ == "__main__":
    main()