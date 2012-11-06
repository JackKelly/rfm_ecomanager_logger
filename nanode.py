from __future__ import print_function
import serial
import json

class NanodeError(Exception):
    """Base class for errors from the Nanode."""


class Nanode(object):
    """Used to manage a Nanode running the rfm_edf_ecomanager code."""
    
    def __init__(self, args, port="/dev/ttyUSB0"):
        self.port = port
        self._open_port()
        self.send_command("m") # manual pairing mode
        self.send_command("d") # delete all TXs
        self.send_command("D") # delete all TRXs
        if args.promiscuous:
            self.send_command("u") # print data from all valid transmitters
        else:
            self.send_command("k") # Only print data from known transmitters
        
    def readjson(self):
        line = self.serial.readline()
        print(line, end="")
        json_line = json.loads(line)         
        return json_line
        
    def _open_port(self):
        self.serial = serial.Serial(self.port, 115200)
        # Deliberately don't catch exception: if connecting to the 
        # Serial port fails then we need to terminate.
        
    def send_command(self, cmd, param=None):
        self.serial.flushInput()
        self.serial.write(cmd)
        self._process_response()
        if param:
            self.serial.write(str(param) + "\r")
            echo = self.serial.readline()
            if echo.strip() != str(param):
                raise NanodeError("Attempted to send command {:s}{:d}, "
                                  "received incorrect echo: {:s}"
                                  .format(cmd, param, echo))
            self._process_response()
                  
    def _process_response(self):
        response = self.serial.readline()
        if response.split()[0] == "ACK":
            print(response) # TODO: this should go to log file
        else:
            raise NanodeError(response)
