#!/usr/bin/python
from __future__ import print_function
import argparse
import logging, logging.handlers
log = logging.getLogger("rfm_ecomanager_logger")
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

def setup_logger(args):
    # Process command line log level
    numeric_level = getattr(logging, args.loglevel.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: {}'.format(args.loglevel))
    
    # Get reference to logger
    logger = logging.getLogger("rfm_ecomanager_logger")
    logger.setLevel(numeric_level)

    # create formatter
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s",
                                  "%y-%m-%d %H:%M:%S")
    
    # create console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    
    # create file handler
    logfile = os.path.dirname(os.path.realpath(__file__)) + "/../rfm_ecomanager_logger.log"     
    fh = logging.handlers.RotatingFileHandler(logfile, maxBytes=1E7, backupCount=20)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    
    # Output first message
    log.info("Starting up. Unixtime = {}".format(time.time()))


def main():    
    args = setup_argparser()
    
    setup_logger(args)
    
    log.info("Please wait for Nanode to initialise...")
    
    try:
        with Nanode(args) as nanode:
            manager = Manager(nanode, args)
            
            if args.edit:
                log.info("Running editing...")
                manager.run_editing()
            else:
                # register SIGINT and SIGTERM handler
                sig_handler = sighandler.SigHandler()
                sig_handler.add_objects_to_stop([nanode, manager])
                                
                # start logging
                manager.run_logging()
    except SystemExit:
        pass
    except:
        log.exception("")

    log.info("shutdown\n")
    logging.shutdown()
    
    
if __name__ == "__main__":
    main()