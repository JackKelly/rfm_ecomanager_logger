from __future__ import print_function
from input_with_cancel import input_with_cancel, input_int_with_cancel

class Sensor(object):
    """Each Transmitter can have 1 to 3 Sensors."""
    
    def __init__(self):
        self.name = ""
        self.log_chan = None
        self.filename = None

    def update_name(self, tx):
        new_name = input_with_cancel("  New name for sensor [{:s}]:".format(self.name))
        if new_name:
            self.name = new_name
        
        log_chan_list = tx.manager.get_log_chan_list()
        default_log_chan = self.log_chan if self.log_chan \
                           else tx.manager.next_free_log_chan()
        while True:
            new_log_chan = input_int_with_cancel(
                                "  New log channel or 0 to not log [{:d}]:"
                                .format(default_log_chan))
        
            if new_log_chan == "":
                self.log_chan = default_log_chan
                break
            else:                
                if new_log_chan in log_chan_list:
                    print("  Log chan {:d} is already in use. "
                          "Please pick another.".format(new_log_chan))
                else:
                    self.log_chan = new_log_chan
                    break
    
        self.update_filename(tx)
    
    def update_filename(self, tx):
        self.filename = tx.manager.args.data_directory + \
                        "channel_{:02d}.dat".format(self.log_chan)
                        
    def log_data_to_disk(self, timecode, watts):
        with open(self.filename, 'a') as data_file:
            data_file.write("{} {}\n".format(timecode, watts))
            # file will close when we leave "with" block

    def __getstate__(self):
        """Used by pickle()"""
        odict = self.__dict__.copy() # copy the dict since we change it
        del odict['filename']
        return odict
