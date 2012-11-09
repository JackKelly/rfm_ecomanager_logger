from __future__ import print_function
from transmitter import Cc_tx, Cc_trx
import pickle
import time
import sys
import sighandler
from nanode import NanodeRestart
from input_with_cancel import *

class Manager(object):
    """ 
    Attributes:
      - nanode (Nanode)
      - transmitters  (dict of Transmitters)
      - args
      
    """
    
    PICKLE_FILE = "radioIDs.pkl"
    
    def __init__(self, nanode, args, sig_handler=sighandler.SigHandler()):
        self.nanode = nanode
        self.args = args
        self.sig_handler = sig_handler

        # if radio_ids exists then open it and load data, tell Nanode
        # how many TXs and TRXs there are and then inform Nanode of
        # each TX and TRX.
        try:
            pkl_file = open(Manager.PICKLE_FILE, "rb")
        except:
            print("No {} file found. Please run with --edit command line option"
                  " to train the system before logging data.")
            sys.exit()
        else:
            self.transmitters = pickle.load(pkl_file)
            pkl_file.close()

            for dummy, tx in self.transmitters.iteritems():
                tx.unpickle()
            
            self._tell_nanode_about_transmitters()

    def _tell_nanode_about_transmitters(self):
        self.nanode.send_command("d") # delete all TXs
        self.nanode.send_command("D") # delete all TRXs        
        if self.transmitters:
            num_txs, num_trxs = self._count_transmitters()
            if num_txs:
                self.nanode.send_command('s', num_txs)
            if num_trxs:
                self.nanode.send_command('S', num_trxs)       
            for dummy, tx in self.transmitters.iteritems():
                tx.add_to_nanode()

    def _count_transmitters(self):
        num_txs = 0
        num_trxs = 0
        for dummy, tx in self.transmitters.iteritems():
            tx.manager = self
            if isinstance(tx, Cc_tx):
                num_txs += 1
            else:
                num_trxs += 1
                
        return num_txs, num_trxs

    def run_logging(self):
        print("Running logging mode. Press CTRL+C to exit.")
        while not self.sig_handler.abort:
            json_line = self._readjson()
            if json_line:
                tx_id = json_line.get("id")
                if tx_id in self.transmitters:
                    self.transmitters[tx_id] \
                        .new_reading(json_line.get("sensors"))

    def _readjson(self):
        try:
            json_line = self.nanode.readjson()
        except NanodeRestart:
            self.nanode.send_init_commands()
            self._tell_nanode_about_transmitters()
            json_line = self.nanode.readjson()
        return json_line

    def get_log_chan_list(self):
        log_ids = []
        for dummy, tx in self.transmitters.iteritems():
            for dummy, sensor in tx.sensors.iteritems():
                if sensor.log_chan:
                    log_ids.append(sensor.log_chan)
        return log_ids
        
    def next_free_log_chan(self):
        log_chan_list = self.get_log_chan_list()
        if log_chan_list:
            return max(log_chan_list)+1
        else:
            return 1
    
    def run_editing(self):
        self._list_transmitters()
        while True:
            print("")
            cmd = raw_input("Enter command (or ? for help): ")
            try:
                if cmd == "?":
                    print("")
                    print("l      : list all known transmitters")
                    print("n      : listen for new transmitter")
                    print("m      : manually enter transmitter ID")
                    print("<index>: edit known transmitter")
                    print("d      : delete known transmitter")
                    print("s      : switch TRX on or off")
                    print("q      : quit")
                elif cmd == "l": self._list_transmitters()
                elif cmd == "n": self._listen_for_new_tx()
                elif cmd == "m": self._manually_enter_id()
                elif cmd.isdigit(): self._edit_transmitter(cmd)
                elif cmd == "d": self._delete_transmitter()
                elif cmd == "s": self._switch_trx()
                elif cmd == "q":
                    print("quit\n") 
                    break
                elif cmd == "": continue
                else:
                    print("Unrecognised command: '{}'\n".format(cmd))
            except Cancel, c:
                print(c)

    def _list_transmitters(self):
        print("")
        print("{:5s}{:>12s}{:>6}{:>8}{:>10}{:>15}"
              .format("INDEX", "RF_ID", "TYPE", "SENSOR", "LOG_CHAN", "NAME"))

        log_chans = self._get_log_chans_and_rf_ids()
        for log_chan, tx_id in log_chans:
            print("{:>5d}{:>12d}{:>6}{}"
                  .format(log_chan, tx_id, self.transmitters[tx_id].TYPE
                          , self.transmitters[tx_id].print_sensors()))
    
    def _edit_transmitter(self, cmd):
        try:
            target_log_chan = int(cmd)
        except ValueError:
            raise Cancel("{} is not an int. Please try again.".format(cmd))
        
        target_tx_id = self._get_tx_id_by_log_chan(target_log_chan)
                
        self.transmitters[target_tx_id].update_name()
        self._pickle()
        
    def _get_tx_id_by_log_chan(self, target_log_chan):
        log_chans = self._get_log_chans_and_rf_ids()

        for log_chan, tx_id in log_chans:
            if log_chan == target_log_chan:
                return tx_id
        
        print(target_log_chan,"could not be found. Please try again.")
        return None
        
    def _get_log_chans_and_rf_ids(self):
        log_chans = []
        for tx_id, tx in self.transmitters.iteritems():
            log_chans.append((tx.sensors[1].log_chan, tx_id))
            
        log_chans.sort()
        return log_chans
        
    def _listen_for_new_tx(self):
        self.nanode.clear_serial()
        WAIT_TIME = 30
        print("Listening for transmitters for 30 seconds...")
        end_time = time.time() + WAIT_TIME
        while time.time() < end_time:
            json_line = self._readjson()
            if not json_line: # emtpy line suggests timeout
                print("No transmitters heard.")
                return
            
            tx_id = json_line.get("id")
                
            # Handle data from Nanode
            if json_line.get("pr"): # pair request
                if self._user_accepts_pairing(json_line):
                    print("Pairing with transmitter...")
                    self._handle_pair_request(json_line.get("pr"))
                    break
            elif tx_id not in self.transmitters:
                if self._user_accepts_pairing(json_line):
                    print("Adding transmitter...")
                    self._add_transmitter(tx_id, json_line.get("type"))
                    self.transmitters[tx_id].add_to_nanode()
                    self.transmitters[tx_id].update_name(json_line.get("sensors"))
                    self._pickle()
                    break

    def _handle_pair_request(self, pr):
        tx_id  = pr["id"]
        if tx_id in self.transmitters.keys():
            print("Pair request received from a TX we already know")
            self.transmitters[tx_id].reject_pair_request()
        else:
            self._add_transmitter(tx_id, pr["type"])
            self.transmitters[tx_id].accept_pair_request()
            self._pickle()

    def _add_transmitter(self, tx_id, tx_type):
        self.transmitters[tx_id] = Cc_tx(tx_id, self) if tx_type=="tx" \
                                   else Cc_trx(tx_id, self)
        
    def _pickle(self):
        output = open(Manager.PICKLE_FILE, "wb")
        pickle.dump(self.transmitters, output)
        output.close()
                                
    def _user_accepts_pairing(self, json_line):
        pair_request = json_line.get("pr")
        if pair_request:
            return yes_no_cancel("Pair request received from {}. Accept? Y/n/c: "
                                       .format(pair_request["id"]))
        else:
            return yes_no_cancel("Unknown transmitter {} with sensors {}. Add? Y/n/c: "
                                       .format(json_line["id"], 
                                               json_line["sensors"]))
    
    def _ask_user_for_index_and_retrieve_id(self):
        tx_id = None
        while not tx_id:
            i = input_int_with_cancel("Enter index of transmitter "
                                      "(or c to cancel): ")
            tx_id = self._get_tx_id_by_log_chan(i)
        return tx_id
    
    def _delete_transmitter(self):
        print("Deleting transmitter...")
        tx_id = self._ask_user_for_index_and_retrieve_id()
        user_accepts = yes_no_cancel("Are you sure you want to delete tx "
                                     " {} ({})? Y/n/c: "
                                    .format(tx_id, self.transmitters[tx_id].print_names()))
        
        if user_accepts:
            print("deleting tx", tx_id)
            self.transmitters[tx_id].delete_from_nanode()
            del self.transmitters[tx_id]
            self._pickle()
        
    def _manually_enter_id(self):
        while True:
            tx_type = input_with_cancel("Is this a 'TX' or 'TRX'? [TRX]: ")
            tx_type = tx_type.upper()
            if tx_type == "":
                tx_type = "TRX"
                break
            elif tx_type == "TRX" or tx_type == "TX":
                break
            else:
                print("'{}' is not a valid tx type. Please enter 'TX' or "
                      "'TRX' or 'c' to cancel.".format(tx_type))
       
        tx_id = input_int_with_cancel("Please enter the {}'s RF ID: "
                                      .format(tx_type))
       
        self._add_transmitter(tx_id, tx_type)
        self.transmitters[tx_id].add_to_nanode()
        self.transmitters[tx_id].update_name()
        self._pickle()

    def _switch_trx(self):
        print("Switching TRX on or off...")
        tx_id = self._ask_user_for_index_and_retrieve_id()
        if self.transmitters[tx_id].TYPE == "TX":
            print("That's a TX not a TRX. We can't switch TXs.")
            return
        
        on_or_off = input_int_with_cancel("On (1) or off (0)? ")
        self.transmitters[tx_id].switch(on_or_off)
        