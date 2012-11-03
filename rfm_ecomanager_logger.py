from __future__ import print_function
from __future__ import division
import json
import serial

class Sensor(object):
    """Each Transmitter can have 1 to 3 Sensors."""
    def __init__(self, name=None, log_chan=None):
        self.name = name
        self.log_chan = log_chan


class Transmitter(object):
    def __init__(self, sensors={}):
        self.sensors = sensors


class Manager(object):
    def __init__(self, nanode):
        self.nanode = nanode
        self.txs = {}
        self.trxs = {}
        
        json_file = open("radioIDs.json")
        self.radio_ids = json.load(json_file)
        json_file.close()
    
    def extract_dict(self, json_data):
        dict = {}
        for tx in json_data:
            if tx.get("sensors"):
                dict[tx.get("id")] = [None,None,None]
                for sensor in tx.get("sensors"):
                    dict[tx.get("id")][sensor.get("s")] = sensor.get("chan")
            else:
                dict[tx.get("id")] = [tx.get("chan")]
                
        return dict


class NanodeError(Exception):
    """Base class for errors from the Nanode."""


class Nanode(object):
    """Used to manage a Nanode running the rfm_edf_ecomanager code."""
    
    def __init__(self, port="/dev/ttyUSB0"):
        self.port = port
        self._open_port()
        
    def _open_port(self):
        self.serial = serial.Serial(self.port, 115200)
        # Deliberately don't catch exception: if connecting to the 
        # Serial port fails then we need to terminate.
        
    def _send_command(self, cmd, param=None):
        self.serial.flushInput()
        self.serial.write(cmd)
        self._process_response()
        if param:
            self.serial.write(str(param) + "\r\n")
            echo = self.serial.readline()
            if echo.strip() != str(param):
                raise NanodeError("Attempted to send command {:s}{:d}, "
                                  "received incorrect echo: {:s}"
                                  .format(cmd, param, echo))
            self._process_response()
            
        
    def _process_response(self):
        response = self.serial.readline()
        if response.split()[0] != "ACK":
            raise NanodeError(response)
            

def send_dict_to_nanode(dict, tx_type):
    
    

def main():
    print("rfm_ecomanager_logger")
    
if __name__ == "__main__":
    main()