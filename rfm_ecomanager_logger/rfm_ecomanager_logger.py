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
   
    parser.add_argument('--log', dest='loglevel', type=str, default='INFO',
                        help='DEBUG or INFO or WARNING (default: INFO)')  
    
    parser.add_argument('--data-directory', dest='data_directory', type=str
                        ,default=""
                        ,help='directory for storing data (default: $DATA_DIR/XYZ/)')
    
    parser.add_argument('--port', dest='port', type=str
                        ,default='/dev/ttyUSB0'
                        ,help='serial port (default: /dev/ttyUSB0)') 
    
    parser.add_argument('--do-not-switch', dest='switch', action='store_const',
                        const=False, default=True, 
                        help="Do not switch TRXs on if they are detected to be off.")
    
    return parser.parse_args()


def pre_process_data_directory(args):

    if args.data_directory:
        # append trailing slash to data_directory if necessary
        args.data_directory = os.path.realpath(args.data_directory)
            
        # if directory doesn't exist then create it
        if not os.path.isdir(args.data_directory):
            if os.path.exists(args.data_directory):
                logging.critical("The path specified as the data directory '{}' "
                              "is not a directory but is a file. Please try again."
                              .format(args.data_directory))
                sys.exit(1)
            else:
                os.makedirs(args.data_directory)
    else: # use default for args.data_directory
        data_dir = os.environ.get("DATA_DIR") 
        if data_dir:
            data_dir = os.path.realpath(data_dir)
            new_subdir_number = 0
            if os.path.isdir(data_dir):
                # Get just the names of the directories within data_dir
                # Taken from http://stackoverflow.com/a/142535/732596
                existing_subdirs = os.walk(data_dir).next()[1]
                existing_subdirs.sort()
                print(existing_subdirs)
                try:
                    new_subdir_number = int(existing_subdirs[-1]) + 1
                except:
                    pass # use default new_subdir_number
                    
            new_subdir_name = "{:03d}".format(new_subdir_number)
            args.data_directory = data_dir + "/" + new_subdir_name
            logging.info("Creating data directory {}".format(args.data_directory))
            os.makedirs(args.data_directory)
                
        else:
            logging.critical("Must set data directory either using environment variable DATA_DIR or command line argument --data-directory")
            sys.exit(1)
            
        
    

    return args


def setup_logger(args):
    numeric_level = getattr(logging, args.loglevel.upper(), None)
    
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: {}'.format(args.loglevel))
    
    logfile = os.path.dirname(os.path.realpath(__file__)) + "/../rfm_ecomanager_logger.log" 

    logging.basicConfig(filename=logfile, 
                        level=numeric_level, 
                        format="%(asctime)s;%(levelname)s;%(message)s", 
                        datefmt="%Y-%m-%d %H:%M:%S")
    
    # send critical and errors to sys.__stderr__
    stderr = logging.StreamHandler(sys.__stderr__)
    stderr.setLevel(logging.WARNING)

    
    logging.info('MAIN: rfm_ecomanager_logger.py starting up. Unixtime = {:.0f}'
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
                logging.info("Running editing...")
                manager.run_editing()
            else:
                # register SIGINT and SIGTERM handler
                sig_handler = sighandler.SigHandler()
                sig_handler.add_objects_to_stop([nanode, manager])
                logging.info("Running logging...")
                manager.run_logging()
    except:
        logging.exception("")
        raise

    print("\nshutdown")
    logging.shutdown()
    
    
if __name__ == "__main__":
    main()