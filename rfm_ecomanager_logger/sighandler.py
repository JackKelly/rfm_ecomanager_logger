import logging
import signal

class SigHandler(object):
    def __init__(self):
        self.objects_to_stop = []
        self._register()
    
    def add_objects_to_stop(self, objects):
        self.objects_to_stop.extend(objects)
    
    def _signal_handler(self, signal_number, frame):
        """Handle SIGINT and SIGTERM.
        
        Required to handle events like CTRL+C and kill.  Sets `abort` to True
        to tell all threads to terminate ASAP.
        """
        
        signal_names = {signal.SIGINT: 'SIGINT', 
                        signal.SIGTERM: 'SIGTERM'}
        
        logging.critical("\nSignal {} received."
                         .format(signal_names[signal_number]))
        
        for obj in self.objects_to_stop:
            obj.abort = True

    def _register(self):
        logging.info("setting signal handlers")
        signal.signal(signal.SIGINT,  self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)