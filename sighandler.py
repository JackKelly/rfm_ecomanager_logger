import logging
import signal

class SigHandler(object):
    def __init__(self):
        self.abort = False
    
    def signal_handler(self, signal_number, frame):
        """Handle SIGINT and SIGTERM.
        
        Required to handle events like CTRL+C and kill.  Sets _abort to True
        to tell all threads to terminate ASAP.
        """
        
        signal_names = {signal.SIGINT: 'SIGINT', signal.SIGTERM: 'SIGTERM'}
        logging.critical("\nSignal {} received."
                                         .format(signal_names[signal_number]))
        self.abort = True

    def register(self):
        logging.info("setting signal handlers")
        signal.signal(signal.SIGINT,  self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)        