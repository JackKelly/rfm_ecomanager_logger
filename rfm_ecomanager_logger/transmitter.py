from __future__ import print_function
import abc
import logging
import time
log = logging.getLogger("rfm_ecomanager_logger")
from sensor import Sensor                   
from input_with_cancel import input_with_cancel

class TransmitterError(Exception):
    """For errors from Transmitter objects"""

class NeedToPickle(TransmitterError):
    """Need to pickle!"""

class Transmitter(object):
    """Abstract base class for representing a single transmitter.
    A transmitter may have multiple sensors.
    """
    
    __metaclass__ = abc.ABCMeta
    
    def __init__(self, rf_id, manager):
        self.id = rf_id
        self.manager = manager
    
    @abc.abstractmethod
    def update_name(self, sensors=None):
        print("\nEditing transmitter {}. Press c to cancel.\n".format(self.id))      

    def accept_pair_request(self):
        print("Pairing with", self.id)
        self.manager.nanode.send_command("p", self.id)
        success = False
        DEADLINE = time.time() + 5
        while time.time() < DEADLINE and not success:
            data = self.manager.nanode.read_sensor_data()
            if data.tx_id == self.id:
                if data.pair_ack:
                    print("Successfully paired with", self.id)
                    self.update_name()
                    success = True
                else:
                    success = False
                    break
            else:
                log.debug("Ignoring {} while waiting for pair ack from {}"
                          .format(data.tx_id, self.id))                
        if not success:
            raise TransmitterError("Failed to pair with {}".format(self.id))            
    
    @abc.abstractmethod
    def reject_pair_request(self, pr):
        pass
    
    def unpickle(self, manager):
        self.manager = manager
        for _, sensor in self.sensors.iteritems():
            sensor.update_filename(self)
            sensor.last_logged_timecode = 0
        
    def add_to_nanode(self):
        self.manager.nanode.send_command(self.ADD_COMMAND, self.id)
        
    def delete_from_nanode(self):
        self.manager.nanode.send_command(self.DEL_COMMAND, self.id)

    def new_reading(self, data):
        for s_id, watts in data.sensors.iteritems():
            s_id = int(s_id)
            if s_id in self.sensors.keys():
                self.sensors[s_id].log_data_to_disk(data.timecode, watts,
                                                    self.get_power_state())
            else:
                log.error("Transmitter {:d} reports a sensor is connected to "
                      "port {:d} but we don't have any info for that sensor id."
                      .format(self.id, s_id))

    def get_power_state(self):
        """Overridden by child classes, if necessary."""
        return None

    def __getstate__(self):
        """Used by pickle()"""
        odict = self.__dict__.copy() # copy the dict since we change it
        del odict['manager']
        return odict
    
    def print_sensors(self):
        string = ""
        first = True
        for sensor_id, sensor in self.sensors.iteritems():
            if first:
                first = False
            else:
                string += "\n" + " "*26
                
            string += "{:>8d}{:^5s}{:>10d}{:>20s}" \
                      .format(sensor_id,
                              "agg" if sensor.agg_chan else "iam", 
                              sensor.log_chan, 
                              sensor.name)
        return string

    def print_names(self):
        string = ""
        first = True
        for dummy, sensor in self.sensors.iteritems():
            if first:
                first = False
            else:
                string += ", "
                
            string += sensor.name
        return string
        

class Cc_trx(Transmitter):
    
    ADD_COMMAND = "N"
    DEL_COMMAND = "R"
    TYPE = "TRX"
    SECONDS_OFF = 12 # if the IAM is unplugged for this length of time
    # or longer then we will switch it to its previous power state
    # when it is powered on again.
    
    def __init__(self, rf_id, manager):
        super(Cc_trx, self).__init__(rf_id, manager)
        self.sensors = {1: Sensor()}
        self.state = 1 # is the IAM on or off?
        self.time_of_last_packet = 0
        self.state_just_changed = False        
        
    def reject_pair_request(self):
        # Add and immediately remove
        self.nanode.send_command("pw", self.id)
        self.nanode.send_command("R", self.id) # remove
        
    def update_name(self, sensors=None):
        super(Cc_trx, self).update_name()
        self.sensors[1].update_name(self)
        
    def get_name(self):
        return self.sensors[1].name
    
    def get_power_state(self):
        """Override."""        
        if self.state_just_changed and self.time_of_last_packet != 0:
            # Don't record a button press to data file if this is the first
            # line of the data file
            return self.state
        else:
            return None

    # Override
    def new_reading(self, data):

        self.state_just_changed = False

        def accept_state_change_and_log():
            self.state = data.state
            self.state_just_changed = True
            log.info("IAM " + self.get_name() + 
                     " state has changed to " + str(self.state))     
        
        # Check if IAM has just changed state.  Either accept that state change
        # or reject it and switch the IAM to the previous state.
        if data.state is not None:
            if data.state != self.state:
                if data.state == 1:
                    # IAM has just turned on. This can ONLY happen if the IAM's
                    # power button has been pressed, so accept this change
                    # without further consideration.
                    accept_state_change_and_log()
                else:
                    # IAM has turned off. Several possible causes:
                    # 1) the IAM's power button has been pressed and we have
                    #    received the IAM's packet notifying us of the button
                    #    press. In this case we accept the change and log
                    #    it to disk.
                    # 2) The IAM's power button has been pressed but we have
                    #    failed to receive notification from the IAM (the IAM
                    #    doesn't do carrier detection or wait for an ACK)
                    # 3) the IAM randomly decided to power off (happens 
                    #    occasionally).  Unfortunately there is no way to 
                    #    discriminate between cases 2 and 3.
                    # 4) mains power has been returned to the IAM (all IAMs
                    #    always start in their 'off' state). In this case we
                    #    want to return the IAM to its previous recorded state.
                    #    We can try to detect this case by checking how long
                    #    the IAM has been off for. 
                    if (data.reply_to_poll is not None and
                        data.reply_to_poll == 0):
                        # IAM's power button was definitely pressed
                        # (We need to check if reply_to_poll is not None
                        # because Older (pre 25/2/13) Nanode code doesn't
                        # have a reply_to_poll item)                        
                        accept_state_change_and_log()
                    elif ((self.time_of_last_packet + Cc_trx.SECONDS_OFF) 
                          > data.timecode):
                        # We heard from the IAM within the last SECONDS_OFF
                        # so this state change is likely to be the result of
                        # an IAM button press that we didn't hear.
                        accept_state_change_and_log()
                    elif self.manager.args.switch:
                        # We haven't heard from the IAM for at least
                        # SECONDS_OFF so let's assume it was unplugged and
                        # plugged in again, in which case we must switch it
                        # to its previous state.
                        self.switch(self.state)

        super(Cc_trx, self).new_reading(data)
        self.time_of_last_packet = data.timecode
    
    # Override
    def unpickle(self, manager):
        super(Cc_trx, self).unpickle(manager)
        self.state = self.__dict__.get('state', 1)
        self.state_just_changed = False
        
    # Override
    def __getstate__(self):
        """Used by pickle()"""
        odict = super(Cc_trx, self).__getstate__()
        del odict['state_just_changed']
        return odict        

    def switch(self, state):
        """Switch IAM on or off.
        Args:
            state (boolean)
        """
        log.info("Switching {:s} to {:d}".format(self.get_name(), state))
        self.manager.nanode.send_command("{:d}".format(state), self.id)

class Cc_tx(Transmitter):
    
    VALID_SENSOR_IDS = [1,2,3]
    ADD_COMMAND = "n"
    DEL_COMMAND = "r"
    TYPE = "TX"

    def __init__(self, rf_id, manager):
        super(Cc_tx, self).__init__(rf_id, manager)        
        self.sensors = {}
        
    def reject_pair_request(self):
        pass # there's nothing we can do for TXs
    
    def update_name(self, detected_sensors=None):
        super(Cc_tx, self).update_name()
        print("Sensor type = TX")
        print("Sensor ID =", self.id)
        
        if self.sensors:
            default_sensor_list = self.sensors.keys()
        elif detected_sensors:
            default_sensor_list = [int(s) for s in detected_sensors.keys()]
            for s in detected_sensors:
                print("Sensor", s, "=", detected_sensors[s], "watts")
        else:
            default_sensor_list = [1]
        
        ask_the_question = True
        while ask_the_question:
            print("List the detected_sensors inputs used on this transmitter,"
                  " separated by a comma. Default="
                  , default_sensor_list, " : ", sep="", end="")
            
            sensor_list_str = input_with_cancel();
    
            if sensor_list_str == "":
                sensor_list = default_sensor_list
                ask_the_question = False
            else:
                sensor_list = []
                for s in sensor_list_str.split(","):
                    try:
                        s = int(s)
                    except:
                        print(s, "not a valid sensor list. Expected format: 1,2,3")
                        ask_the_question = True
                        break
                    else:
                        if s in Cc_tx.VALID_SENSOR_IDS:
                            sensor_list.append(int(s))
                            ask_the_question = False
                        else:
                            print(s, "is not a valid sensor number.")
                            ask_the_question = True
                            break

        for s in sensor_list:
            if s not in self.sensors.keys():
                self.sensors[s] = Sensor()
        
        for s in self.sensors:
            print("SENSOR", s, ":")
            self.sensors[s].update_name(self)
    
