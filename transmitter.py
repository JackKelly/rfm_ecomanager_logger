from __future__ import print_function
import abc
from nanode import Nanode
from sensor import Sensor                   


class TransmitterError(Exception):
    """For errors from Transmitter objects"""


class Transmitter(object):
    __metaclass__ = abc.ABCMeta
    
    def __init__(self, rf_id, manager):
        self.id = rf_id
        self.manager = manager
    
    @abc.abstractmethod
    def update_name(self, sensors=None):
        pass

    def accept_pair_request(self):
        print("Pairing with", self.id)
        self.manager.nanode.send_command("p", self.id)
        json_line = self.manager.nanode.readjson()
        if json_line.get("pw").get("id") == self.id:
            print("Successfully paired with", self.id)
            self.update_name()
        else:
            raise TransmitterError("Failed to pair with", self.id)            
    
    @abc.abstractmethod
    def reject_pair_request(self, pr):
        pass
        
    def add_to_nanode(self):
        self.manager.nanode.send_command(self.ADD_COMMAND, self.id)
    
    def new_reading(self, sensors):
        for sensor, watts in sensors.iteritems():
            sensor = int(sensor)
            if sensor in self.sensors.keys():
                self.sensors[sensor].new_reading(int(watts))
            else:
                print("Transmitter {:d} reports a sensor is connected to "
                      "port {:d} but we don't have any info for that sensor."
                      .format(self.id, sensor))
    
    def __getstate__(self):
        """Used by pickle()"""
        odict = self.__dict__.copy() # copy the dict since we change it
        del odict['manager']
        return odict


class Cc_trx(Transmitter):
    
    ADD_COMMAND = "N"
    
    def __init__(self, rf_id, manager):
        super(Cc_trx, self).__init__(rf_id, manager)
        self.sensors = {1: Sensor(self)}
        
    def reject_pair_request(self):
        # Add and immediately remove
        self.nanode.send_command("pw", self.id)
        self.nanode.send_command("R", self.id) # remove
        
    def update_name(self, sensors=None):
        self.sensors[1].update_name()
    

class Cc_tx(Transmitter):
    
    VALID_SENSOR_IDS = [1,2,3]
    ADD_COMMAND = "n"

    def __init__(self, rf_id, manager):
        super(Cc_tx, self).__init__(rf_id, manager)        
        self.sensors = {}
        
    def reject_pair_request(self):
        pass
    
    def update_name(self, sensors=None):
        print("Sensor type = TX")
        print("Sensor ID =", self.id)
        
        if self.sensors:
            default_sensor_list = self.sensors.keys()
        elif sensors:
            default_sensor_list = [int(s) for s in sensors.keys()]
            for s in sensors:
                print("Sensor", s, "=", sensors[s], "watts")
        else:
            default_sensor_list = [1]
        
        ask_the_question = True
        while ask_the_question:
            print("List the sensors inputs used on this transmitter,"
                  " separated by a comma. Default="
                  , default_sensor_list, " : ", sep="", end="")
            
            sensor_list_str = raw_input();
    
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
                self.sensors[s] = Sensor(self)
        
        for s in self.sensors:
            print("SENSOR", s, ":")
            self.sensors[s].update_name()
    
