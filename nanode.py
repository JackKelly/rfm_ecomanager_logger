from __future__ import print_function, division
import serial
import json
import logging
import select
import time

class NanodeError(Exception):
    """Base class for errors from the Nanode."""


class NanodeRestart(NanodeError):
    """Nanode has restarted."""
    
    
class NanodeTooManyRetries(NanodeError):
    """Nanode has restarted."""
    

class Data(object):
    """Struct for storing data from Nanode"""


class Nanode(object):
    """Used to manage a Nanode running the rfm_edf_ecomanager code."""
    
    MAX_RETRIES = 20
    MAX_ACCEPTABLE_LATENCY = 0.015 # in seconds
    TIME_OFFSET_UPDATE_PERIOD = 60*10 # in seconds
    MAX_ACCEPTABLE_DRIFT = 0.5 # in seconds
    
    def __init__(self, args):
        self.abort = False        
        self._args = args
        self._open_port()
        try:
            self.init_nanode()
        except NanodeRestart:
            self.init_nanode() # re-send init commands after restart
        
    def init_nanode(self):
        logging.debug("Sending init commands to Nanode...")
        self.clear_serial()
        self._serial.write("\r")        
        self.send_command("v", 4) # don't show any debug log messages
        self.send_command("m") # manual pairing mode
        if self._args.edit:
            self.send_command("u") # print data from all valid transmitters
        else:
            self.send_command("k") # Only print data from known transmitters
        self._time_offset = None                    
        self._first_nanode_time = self._get_nanode_time()[1]
        self._set_time_offset()
    
    def _set_time_offset(self):
        retries = 0
        while retries < Nanode.MAX_RETRIES and not self.abort:
            retries += 1
            start_time, nanode_time, end_time = self._get_nanode_time()
            if nanode_time:
                # Nanode sends time 10ms after receipt of the 't' command
                new_time_offset = end_time - (nanode_time / 1000)
                
                # Test if new_time_offset is stupidly different from the
                # old time offset
                if self._time_offset and (
                  new_time_offset > self._time_offset+Nanode.MAX_ACCEPTABLE_DRIFT or
                  new_time_offset < self._time_offset-Nanode.MAX_ACCEPTABLE_DRIFT):
                    continue  
                
                # Test
                test_time = new_time_offset + (self._get_nanode_time()[1] / 1000)                
                if (test_time > time.time()+Nanode.MAX_ACCEPTABLE_DRIFT or
                    test_time < time.time()-Nanode.MAX_ACCEPTABLE_DRIFT):
                    logging.debug("test_time too dissimilar to time.time(). diff={}"
                                  .format(test_time - time.time()) )
                    continue
                
                # Log time offset details
                logging.debug("Updated time_offset to {}".format(new_time_offset))
                if self._time_offset:
                    logging.debug("  was {}, diff is {}"
                                  .format(self._time_offset, 
                                          new_time_offset-self._time_offset))
                
                # If we get to here then new_time_offset is sane so save it
                self._time_offset = new_time_offset
                self._deadline_to_update_time_offset = start_time + \
                                     Nanode.TIME_OFFSET_UPDATE_PERIOD
                break
    
    def _get_nanode_time(self):
        retries = 0
        while retries < Nanode.MAX_RETRIES and not self.abort:
            retries += 1
            self._serial.flushInput()
            start_time = time.time()
            self._serial.write("t")
            nanode_time = self._readline()
            end_time = time.time()
            latency = end_time - start_time
            logging.debug("latency = {}".format(latency))
            
            if latency > Nanode.MAX_ACCEPTABLE_LATENCY:
                logging.debug("Latency {} too high".format(latency))
                nanode_time = None
                continue            

            try:
                nanode_time = int(nanode_time)
            except:
                logging.debug("Failed to convert {} to an int.".format(nanode_time))
                nanode_time = None
                continue
            else:
                break
        
        return start_time, nanode_time, end_time
    
    def clear_serial(self):
        self._serial.flushInput()
    
    def read_sensor_data(self):           
        json_line = self._readjson()
        if json_line:
            t = time.time()
            data = Data()
            data.is_pairing_request = True if json_line.get("pr") else False
            if data.is_pairing_request:
                json_line = json_line.get("pr")
            
            data_time = json_line.get("t")
            if self._deadline_to_update_time_offset < time.time():
                self._set_time_offset()
            elif data_time < self._first_nanode_time: # roll-over of Nanode's clock  
                logging.debug("Rollover detected.")              
                self._first_nanode_time = data_time
                self._set_time_offset()
                
            data.timecode = self._time_offset + (data_time / 1000)
            logging.debug("ETA={:.3f}, time received={:.3f}, diff={:.3f}"
                  .format(data.timecode, t, data.timecode-t))           
            data.timecode = int(round(data.timecode))
            
            data.sensors  = json_line.get("sensors")
            data.tx_id    = json_line.get("id")
            data.tx_type  = json_line.get("type")
            return data
        else:
            return None
    
    def _readjson(self):
        json_line = None
        line = self._readline()
        if line and line[0] == "{":
            json_line = json.loads(line)
        return json_line
        
    def _readline(self, ignore_json=False):
        retries = 0
        while retries < Nanode.MAX_RETRIES and not self.abort:
            retries += 1
            
            try:
                line = self._serial.readline().strip()
            except select.error:
                if self.abort:
                    logging.debug("Caught select.error but this is nothing to "
                                  "worry about because it was caused by keyboard "
                                  "interrupt.")
                    return ""
                else:
                    raise
                
            if line == "EDF IAM Receiver":
                continue # try again
            elif line == "Finished init":
                logging.info("Nanode restart detected")
                raise NanodeRestart()
            elif line and ignore_json and line[0]=="{":
                continue
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
        logging.debug("Opening port {}".format(self._args.port))
        self._serial = serial.Serial(port=self._args.port, baudrate=115200
                                    ,timeout=30)
        # Deliberately don't catch exception: if connecting to the 
        # Serial port fails then we need to terminate.
        
    def send_command(self, cmd, param=None):
        logging.debug("send_command(cmd={}, param={})".format(cmd, param))
        self._serial.flushInput()
        self._serial.write(cmd)
        self._process_response()
        if param:
            self._serial.write(str(param))
            self._serial.write("\r")
            echo = self._readline(ignore_json=True)
            if echo != str(param):
                raise NanodeError("Attempted to send command {} {}, "
                                  "received incorrect echo: {}"
                                  .format(cmd, param, echo))
            self._process_response()
                  
    def _process_response(self):
        retries = 0
        while retries < Nanode.MAX_RETRIES and not self.abort:
            retries += 1
            response = self._readline(ignore_json=True).split()
            if not response:
                continue # retry if we get a blank line
            elif response[0] == "ACK":
                break # success!          
            elif response[0] == "NAK":
                raise NanodeError(response)
            
        self._throw_exception_if_too_many_retries(retries) 
        
    def __enter__(self):
        return self  

    def __exit__(self, type, value, traceback):
        logging.debug("Nanode __exit__")
        self._serial.close()