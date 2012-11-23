from __future__ import print_function
from input_with_cancel import input_with_cancel, input_int_with_cancel, yes_no_cancel

MAX_POWER_FOR_AGG_CHAN = 10000
MAX_POWER_FOR_IAM_CHAN =  3200

class Sensor(object):
    """Each Transmitter can have 1 to 3 Sensors."""
    
    def __init__(self):
        self.name = ""
        self.log_chan = None
        self.filename = None
        self.agg_chan = False

    def update_name(self, tx):
        new_name = input_with_cancel("  New name for sensor [{:s}]:".format(self.name))
        if new_name:
            self.name = new_name
        
        if self.name.lower() in ["agg", "aggregate", "mains"]:
            self.agg_chan = True
        
        self.agg_chan = yes_no_cancel("  Is this an aggregate channel?", self.agg_chan)
        
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
        self.filename = tx.manager._args.data_directory + \
                        "channel_{:d}.dat".format(self.log_chan)
                        
    def log_data_to_disk(self, timecode, watts):
        if self.log_chan == 0:
            return
        
        if self.agg_chan:
            if watts > MAX_POWER_FOR_AGG_CHAN:
                return
        else:
            if watts > MAX_POWER_FOR_IAM_CHAN:
                return
        
        with open(self.filename, 'a') as data_file:
            data_file.write("{:d} {:d}\n".format(timecode, watts))
            # file will close when we leave "with" block

    def __getstate__(self):
        """Used by pickle()"""
        odict = self.__dict__.copy() # copy the dict since we change it
        del odict['filename']
        return odict
