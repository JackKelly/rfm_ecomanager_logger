from __future__ import print_function
from input_with_cancel import input_with_cancel, input_int_with_cancel, yes_no_cancel
import logging
log = logging.getLogger("rfm_ecomanager_logger")

# The max power for each sensor reading is capped to remove
# insanely large values (probably caused by corrupt RF packets)
MAX_POWER_FOR_AGG_CHAN = 20000
MAX_POWER_FOR_IAM_CHAN =  4000 # 4000W = 17A x 230V

# ignore a sample which arrives less than
# this number of seconds after previous recorded sample 
MIN_SAMPLE_PERIOD = 3

class Sensor(object):
    """Each Transmitter can have 1 to 3 Sensors."""
    
    def __init__(self):
        self.name = ""
        self.log_chan = None
        self.filename = None
        self.agg_chan = False
        self.last_logged_timecode = 0

    def update_name(self, tx):
        new_name = input_with_cancel("  New name for sensor [{:s}]:".format(self.name))
        if new_name:
            self.name = new_name
        
        if self.name.lower() in ["agg", "aggregate", "mains", "whole_house",
                                 "whole house", "wholehouse", "whole-house"]:
            self.agg_chan = True
        
        self.agg_chan = yes_no_cancel("  Is this an aggregate (whole-house) "
                                      " channel?", self.agg_chan)
        
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
                        "/channel_{:d}.dat".format(self.log_chan)
                        
    def log_data_to_disk(self, timecode, watts, new_state=None):
        log.debug("log_data_to_disk {} {} {} {}"
                  .format(self.filename, self.name, timecode, watts))

        if self.log_chan == 0:
            log.debug("Not logging to disk because log_chan == 0")
            return
        
        # Filter insanely high values (these are almost certainly
        # measurement errors)
        if self.agg_chan:
            if watts > MAX_POWER_FOR_AGG_CHAN:
                log.debug("Not logging to disk because watts {} >"
                          " MAX_POWER_FOR_AGG_CHAN {}"
                          .format(watts, MAX_POWER_FOR_AGG_CHAN))
                return
        else: # IAM channel
            if watts > MAX_POWER_FOR_IAM_CHAN:
                log.debug("Not logging to disk because watts {} >"
                          " MAX_POWER_FOR_IAM_CHAN {}"
                          .format(watts, MAX_POWER_FOR_IAM_CHAN))
                return
        
        # Ignore 2 samples in quick succession
        if self.last_logged_timecode > (timecode - MIN_SAMPLE_PERIOD):
            log.debug("Not logging to disk because sample arrived too soon"
                      " after last recorded sample")
            return
        
        # If we get to here then write to disk
        with open(self.filename, 'a') as data_file:            
            data_file.write("{:d} {:d}".format(timecode, watts))
            if new_state is None:
                data_file.write("\n")
            else:                                
                data_file.write(" {:d}\n".format(new_state))
            self.last_logged_timecode = timecode
            # file will close when we leave "with" block        

    def __getstate__(self):
        """Used by pickle()"""
        odict = self.__dict__.copy() # copy the dict since we change it
        del odict['filename']
        return odict
