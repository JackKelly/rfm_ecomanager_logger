from __future__ import print_function
import serial
import json
import logging

class NanodeError(Exception):
    """Base class for errors from the Nanode."""


class NanodeRestart(NanodeError):
    """Nanode has restarted."""
    
    
class NanodeTooManyRetries(NanodeError):
    """Nanode has restarted."""
    

class Nanode(object):
    """Used to manage a Nanode running the rfm_edf_ecomanager code."""
    
    MAX_RETRIES = 5
    
    def __init__(self, args, port="/dev/ttyUSB0"):
        self.port = port
        self.args = args
        self._open_port()
        try:
            self.send_init_commands()
        except NanodeRestart:
            self.send_init_commands() # re-send init commands after restart
        
    def send_init_commands(self):
        logging.debug("Sending init commands to Nanode...")
        self.send_command("v", 4) # don't show any debug log messages
        self.send_command("m") # manual pairing mode
        if self.args.train:
            self.send_command("u") # print data from all valid transmitters
        else:
            self.send_command("k") # Only print data from known transmitters        
        
    def readjson(self):
        json_line = None
        while True:
            line = self._readline()
            if line and line[0] == "{":
                json_line = json.loads(line)
                break
        return json_line
        
    def _readline(self):
        retries = 0
        while retries < Nanode.MAX_RETRIES:
            retries += 1
            line = self.serial.readline().strip()
            if line == "EDF IAM Receiver":
                continue # try again
            elif line == "Finished init":
                logging.info("Nanode restart detected")
                raise NanodeRestart()
            else: # line is not restart text, but may be empty
                if line:
                    logging.debug("NANODE: {}".format(line.strip()))                
                break

        self._throw_exception_if_too_many_retries(retries)        
        return line
    
    def _throw_exception_if_too_many_retries(self, retries):
        if retries == Nanode.MAX_RETRIES:
            raise NanodeTooManyRetries("Failed to receive a valid response "
                              "after {:d} times".format(retries))
        
    def _open_port(self):
        logging.debug("Opening port {}".format(self.port))
        self.serial = serial.Serial(port=self.port, baudrate=115200, timeout=1)
        # Deliberately don't catch exception: if connecting to the 
        # Serial port fails then we need to terminate.
        
    def send_command(self, cmd, param=None):
        logging.debug("send_command(cmd={}, param={})".format(cmd, param))
        self.serial.flushInput()
        self.serial.write(cmd)
        self._process_response()
        if param:
            self.serial.write(str(param) + "\r")
            echo = self._readline()
            if echo != str(param):
                raise NanodeError("Attempted to send command {:s}{:d}, "
                                  "received incorrect echo: {:s}"
                                  .format(cmd, param, echo))
            self._process_response()
                  
    def _process_response(self):
        retries = 0
        while retries < Nanode.MAX_RETRIES:
            retries += 1
            response = self._readline().split()
            if not response:
                continue # retry if we get a blank line
            elif response[0] == "ACK":
                break # success!
            elif response[0][0] == "{":
                continue # ignore this JSON and read next line            
            elif response[0] == "NAK":
                raise NanodeError(response)
            
        self._throw_exception_if_too_many_retries(retries)   