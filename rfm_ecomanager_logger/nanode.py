from __future__ import print_function, division
import serial
import json
import logging
log = logging.getLogger("rfm_ecomanager_logger")
import select
import time
import sys

class NanodeError(Exception):
    """Base class for errors from the Nanode."""


class NanodeRestart(NanodeError):
    """Nanode has restarted."""
    
    
class NanodeTooManyRetries(NanodeError):
    """Nanode has restarted."""
    
class NanodeDataWaiting(NanodeError):
    """Data is waiting yet this function needs a clear input buffer.
    Caller must read and process data or flush before calling this function again.
    The NanodeDataWaiting object may contain a line of data."""

class Data(object):
    """Struct for storing data from Nanode"""


class Nanode(object):
    """Used to manage a Nanode running the rfm_edf_ecomanager code."""
    
    MAX_RETRIES = 20
    MAX_ACCEPTABLE_LATENCY = 0.2 # in seconds
    TIME_OFFSET_UPDATE_PERIOD = 60*10 # in seconds
    MAX_ACCEPTABLE_DRIFT = 0.5 # in seconds
    TIMEOUT = 1 # serial timeout in seconds
    
    def __init__(self, args):
        self.abort = False        
        self.args = args
        self._deadline_to_update_time_offset = 0        
        self._open_port()
        try:
            self.init_nanode()
        except NanodeRestart:
            self.init_nanode() # re-send init commands after restart
        
    def init_nanode(self):
        log.info("Sending init commands to Nanode...")
        retries = 2
        while retries > 0 and not self.abort:
            retries -= 1
            self.flush()
            self._serial.write("\r")
            
            # Turn off LOGGING on the Nanode if necessary
            try:
                self.send_command("v", 4) # don't show any debug log messages
            except NanodeRestart:
                continue # retry
            except NanodeError:
                pass # if Nanode code was compiled without LOGGING
            
            # Other Nanode config commands...
            self.send_command("m") # manual pairing mode
            self.send_command("k") # Only print data from known transmitters
            self._time_offset = None
            self._last_nanode_time = 0
            break
        
        # Set time offset
        if self.args.time_correction:
            retries = 5
            while retries > 0 and not self.abort:
                retries -= 1
                log.debug("Setting _last_nanode_time and _time_offset for"
                          " first time. Retries left={}".format(retries))
                self.flush()           
                try:
                    self._last_nanode_time = self._get_nanode_time()[1]
                    self._set_time_offset()
                except NanodeDataWaiting:
                    pass
                else:
                    break
        
    def _set_time_offset(self):
        """
        Returns nothing but sets self._last_nanode_time if successful.
        
        Raises:
                NanodeDataWaiting: Data is available on the serial port,
                caller must empty input buffer and retry.
        """
        
        retries = 0
        log.debug("_set_time_offset()")
        while retries < Nanode.MAX_RETRIES and not self.abort:
            retries += 1
            start_time, nanode_time, end_time = self._get_nanode_time() # don't catch NanodeDataWaiting exception
            if nanode_time:
                # Nanode sends time 10ms after receipt of the 't' command
                new_time_offset = ((start_time + end_time) / 2) - (nanode_time / 1000)
                
                # Detect rollover
                if nanode_time < self._last_nanode_time:
                    roll_over_detected = True
                    log.info("Rollover detected.")            
                else: 
                    roll_over_detected = False 
                
                # Test if new_time_offset is stupidly different from the
                # old time offset
                if self._time_offset and not roll_over_detected and (
                  new_time_offset > self._time_offset+Nanode.MAX_ACCEPTABLE_DRIFT or
                  new_time_offset < self._time_offset-Nanode.MAX_ACCEPTABLE_DRIFT):
                    log.debug("new_time_offset is too dissimilar to self._time_offset")
                    continue  
                
                # Test
                test_time = new_time_offset + (self._get_nanode_time()[1] / 1000)                
                if (test_time > time.time()+Nanode.MAX_ACCEPTABLE_DRIFT or
                    test_time < time.time()-Nanode.MAX_ACCEPTABLE_DRIFT):
                    log.debug("test_time too dissimilar to time.time(). diff={}"
                                  .format(test_time - time.time()) )
                    continue
                
                # Log time offset details
                log.debug("Updated time_offset to {}".format(new_time_offset))
                if self._time_offset:
                    log.debug("  was {}, diff is {}"
                                  .format(self._time_offset, 
                                          new_time_offset-self._time_offset))
                
                # If we get to here then new_time_offset is sane so save it
                self._time_offset = new_time_offset
                self._deadline_to_update_time_offset = start_time + \
                                     Nanode.TIME_OFFSET_UPDATE_PERIOD
                break
    
    def _get_nanode_time(self):
        """
        Asks the Nanode for the number of milliseconds since it started.
        
        Returns:
            start_time (float): UNIX time immediately before asking Nanode 
                for its time
                
            nanode_time (int): Number of milliseconds since Nanode started
            
            end_time (float): UNIX time immediately after receiving 
                Nanode's time
        
        Raises:
            NanodeDataWaiting: If data is available on the serial port,
                then a NanodeDataWaiting object is returned, containing
                either an empty string or a line of data from the Nanode.
        """        
        retries = 0
        log.debug("_get_nanode_time()")
        while retries < Nanode.MAX_RETRIES and not self.abort:
            retries += 1
            
            # check if any data is waiting for us
            n_waiting = self._serial.inWaiting() 
            if n_waiting > 0:
                log.debug("{} chars waiting".format(n_waiting))
                raise NanodeDataWaiting()
            
            # ask Nanode for its time and also record the round-trip time
            start_time = time.time()
            self._serial.write("t")
            nanode_time = self._readline()
            end_time = time.time()

            try:
                nanode_time = int(nanode_time)
            except:
                # The returned line is not an int so is probably a data line
                # so pass this line back to the caller so the caller can
                # either process this data or discard it.
                log.debug("Failed to convert {} to an int.".format(nanode_time))
                raise NanodeDataWaiting(nanode_time) # pass this non-int text up to caller
            else:            
                latency = end_time - start_time
                log.debug("nanode_time= {}, latency = {}".format(nanode_time, latency))
                
                if latency < Nanode.MAX_ACCEPTABLE_LATENCY:
                    break # we're done
                else:
                    log.debug("Latency {} too high".format(latency))
                    nanode_time = None
                    # try again

        return start_time, nanode_time, end_time
    
    def read_sensor_data(self, retries=MAX_RETRIES):   
        line = None
        json_line = None
        # Decide if we need to update self._time_offset
        if (self.args.time_correction and 
            time.time() > self._deadline_to_update_time_offset):
            
            log.debug("Time to update _time_offset")
            try:
                self._set_time_offset()
            except NanodeDataWaiting, e:
                # If a NanodeDataWaiting exception is thrown then this may be
                # because sensor data arrived from the Nanode
                # when the set_time_offset function read the serial port.
                # Hence we should process this data if it is valid JSON.
                log.debug(e)
                log.debug("Data is waiting so won't update time on this cycle")
                line = str(e)

        if not line:
            # If data hasn't already been loaded from the NanodeDataWaiting
            # exception then read it from the serial port
            line = self._readline(retries=retries)
            
        # Record time immediately after _readline returns.
        t = time.time()
            
        # Convert string to JSON object
        if line and isinstance(line, basestring) and line[0]=="{":
            try:
                json_line = json.loads(line)
            except:
                json_line = None
        
        # Process JSON object
        if json_line:
            log.debug("LINE: {}".format(json_line))            
            data = Data()
            
            # Handle "pair with" responses
            if json_line.get("pw"):
                data.pair_ack = True
                data.tx_id = json_line.get("pw").get("id")
                data.tx_type = json_line.get("pw").get("type")
                return data
            else:
                data.pair_ack = False
            
            data.is_pairing_request = True if json_line.get("pr") else False
            if data.is_pairing_request:
                json_line = json_line.get("pr")
            else:
                # Handle time                
                if self.args.time_correction:
                    nanode_time = json_line.get("t")
                    
                    if nanode_time < self._last_nanode_time: # roll-over of Nanode's clock
                        log.info("Roll-over detected")
                        # nanode's time is a uint32:
                        nanode_time += 2**32
                        # ensure we update time offset on next cycle:
                        self._deadline_to_update_time_offset = time.time() 
                    
                    self._last_nanode_time = nanode_time
                    
                    data.timecode = self._time_offset + (nanode_time / 1000)
                    log.debug("ETA={:.3f}, time received={:.3f}, diff={:.3f}"
                          .format(data.timecode, t, data.timecode-t))
                else:
                    data.timecode = t
                
                data.timecode = int(round(data.timecode))
                
                data.sensors  = json_line.get("sensors")
                
            data.tx_id    = json_line.get("id")
            data.tx_type  = json_line.get("type")
            data.state    = json_line.get("state")
            data.reply_to_poll = json_line.get("reply_to_poll")
            if data.reply_to_poll:
                data.reply_to_poll = int(data.reply_to_poll)
            return data

           
    def _readline_with_exception_handling(self):
        """Wrap serial.readline() with exception handling."""
        try:
            log.debug("Waiting for line from Nanode")
            line = self._serial.readline().strip()
        except select.error:
            if self.abort:
                log.debug("Caught select.error but this is nothing to "
                              "worry about because it was caused by keyboard "
                              "interrupt.")
                return ""
            else:
                raise
        except serial.SerialException:
            log.exception("")
            log.info("Attempting to restart serial connection and Nanode:")
            self._serial.close()
            time.sleep(1)
            self._open_port()
            log.info("Up and running again.")
            raise NanodeRestart()
        except serial.serialutil.SerialException:
            log.critical("Is the Nanode plugged into port {}?".format(self.args.port))
            sys.exit(1)
        else:
            log.debug("From Nanode: {}".format(line))                
            return line
        
    def flush(self):
        """
        Flush the serial port.
        
        Just using serial.flushInput() appeared to render the serial port
        unreadable if the buffer was full.
        """
        
        log.debug("Flushing serial input...")
        timeout = self._serial.timeout
        self._serial.timeout = 0
        self._serial.readall() # flush the serial port (flushInput() seems to sometimes stop us from getting any further data)
        self._serial.timeout = timeout
        self._serial.flushInput()
        self._serial.flush()
        log.debug("Done flushing!")
    
    def _readline(self, ignore_json=False, retries=MAX_RETRIES):
        """
        Raises:
            - NanodeRestart
            - NanodeTooManyRetries
        """
        startup_seq = ["EDF IAM Receiver",
                       "SPI initialised", 
                       "Attaching interrupt", 
                       "Interrupt attached", 
                       "Finished init"]
        
        while retries >= 0 and not self.abort:
            retries -= 1
            log.debug("retries left = {}".format(retries))
            line = self._readline_with_exception_handling()
            if line:
                if line in startup_seq: # Handle Nanode's startup sequence
                    
                    # Extend timeout temporarily because the delay between
                    # init lines can be several seconds.
                    self._serial.timeout = 3
                    
                    # nanode_init_ok encodeds whether the Nanode startup
                    # sequence is progressing as expected.
                    # Set it true before the for loop just in case we never
                    # enter the for loop because line == startup_seq[-1]
                    nanode_init_ok = True 
                    
                    # Loop through rest of startup commands
                    for i in range(startup_seq.index(line), len(startup_seq)):
                        log.info("Part {}/{} of Nanode init sequence detected."
                                 .format(i+1, len(startup_seq)))
                        if line == startup_seq[i]:
                            nanode_init_ok = True
                        else:
                            log.info("Nanode crashed during startup. "
                                     "Attempting serial restart")
                            self._serial.close()
                            self._open_port()
                            nanode_init_ok = False
                            break
                        
                        line = self._readline_with_exception_handling()
                        
                    self._serial.timeout = Nanode.TIMEOUT
                        
                    if nanode_init_ok:
                        log.info("Nanode has finished initialising")
                        raise NanodeRestart()

                elif ignore_json and line[0]=="{":
                    continue
                else: # line is something we should return              
                    return line

        if not self.abort:
            raise NanodeTooManyRetries("Nanode::_readline() Failed after multiple retries.")
    
    def _throw_exception_if_too_many_retries(self, retries):
        if retries == Nanode.MAX_RETRIES:
            raise NanodeTooManyRetries("Failed to receive a valid response "
                              "after {:d} times".format(retries))
        
    def _open_port(self):
        log.info("Opening port {}".format(self.args.port))
        try:
            self._serial = serial.Serial(port=self.args.port, 
                                         baudrate=115200,
                                         timeout=Nanode.TIMEOUT) # timeout in seconds
        except serial.serialutil.SerialException:
            log.critical("Is the Nanode plugged into port {}?".format(self.args.port))
            sys.exit(1)
        else:
            log.info("Successfully opened port {}".format(self.args.port))

        
    def send_command(self, cmd, param=None):
        cmd = str(cmd)
        log.debug("send_command(cmd={}, param={})".format(cmd, str(param)))
        self.flush()
        self._serial.write(cmd)
        self._process_response()
        if param:
            param = str(param)
            self._serial.write(param)
            self._serial.write("\r")
            echo = self._readline(ignore_json=True)
            if echo != param:
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

    def __exit__(self, _type, value, traceback):
        log.debug("Nanode __exit__")
        self._serial.close()
