from __future__ import print_function

class Sensor(object):
    """Each Transmitter can have 1 to 3 Sensors."""
    
    def __init__(self, transmitter):
        self.name = ""
        self.log_chan = None
        self.tx = transmitter

    def update_name(self):
        new_name = raw_input("  New name for sensor [{:s}]:".format(self.name))
        if new_name:
            self.name = new_name
        
        log_chan_list = self.tx.manager.get_log_chan_list()
        
        default_log_chan = self.log_chan if self.log_chan \
                           else self.tx.manager.next_free_log_chan()
                
        while True:
            new_log_chan_str = raw_input("  New log channel or 0 to not log [{:d}]:"
                                         .format(default_log_chan))
        
            if new_log_chan_str:
                try:
                    new_log_chan = int(new_log_chan_str)
                except:
                    print(new_log_chan_str, "is not a number. Please try again.")
                else:                    
                    if new_log_chan and new_log_chan in log_chan_list:
                        print("  Log chan {:d} is already in use. "
                              "Please pick another.".format(new_log_chan))
                    else:
                        self.log_chan = int(new_log_chan_str)
                        break
            else:
                self.log_chan = default_log_chan
                break
    
    def new_reading(self, watts):
        print(self.log_chan, self.name, watts)
        
#    def __getstate__(self):
#        """Used by pickle()"""
#        odict = self.__dict__.copy() # copy the dict since we change it
#        del odict['tx']
#        return odict        
