from __future__ import print_function
from transmitter import Cc_tx, Cc_trx
import pickle
import time
import sys
import logging
from nanode import NanodeRestart
from input_with_cancel import *

class Manager(object):
    """ 
    Attributes:
      - nanode (Nanode)
      - transmitters  (dict of Transmitters)
      - _args
      
    """
    
    PICKLE_FILE = "radioIDs.pkl"
    
    def __init__(self, nanode, args):
        self.nanode = nanode
        self._args = args
        self.abort = False

        # if radio_ids exists then open it and load data, tell Nanode
        # how many TXs and TRXs there are and then inform Nanode of
        # each TX and TRX.
        try:
            pkl_file = open(Manager.PICKLE_FILE, "rb")
        except:
            print(Manager.PICKLE_FILE, "file found. Please run with --edit command line option"
                  " to train the system before logging data.")
            sys.exit()
        else:
            self.transmitters = pickle.load(pkl_file)
            pkl_file.close()

            for dummy, tx in self.transmitters.iteritems():
                tx.unpickle(self)
            
            self._tell_nanode_about_transmitters()
            
            self._create_labels_file()
            
    def _create_labels_file(self):
        log_chans = []
        for dummy, tx in self.transmitters.iteritems():
            for dummy, sensor in tx.sensors.iteritems():
                log_chans.append((sensor.log_chan, sensor.name))
        
        log_chans.sort()

        with open(self._args.data_directory + "labels.dat", "w") as labels_file:
            for log_chan, name in log_chans:
                labels_file.write("{:d} {:s}\n".format(log_chan, name))
            
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
        while not self.abort:
            data = self._read_sensor_data()
            if data:
                if data.tx_id in self.transmitters:
                    self.transmitters[data.tx_id] \
                        .new_reading(data)
                else:
                    logging.error("Unknown TX: {}".format(data.tx_id))

    def _read_sensor_data(self):
        while True:
            try:
                data = self.nanode.read_sensor_data()
            except NanodeRestart:
                self.nanode.init_nanode()
                self._tell_nanode_about_transmitters()
            else:
                break
        return data

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
                elif cmd == "q": break
                elif cmd == "" : continue
                else:
                    print("Unrecognised command: '{}'\n".format(cmd))
            except Cancel, c:
                print(c)

    def _list_transmitters(self):
        print("")
        print("{:5s}{:>12s}{:>6}{:>8}{:>10}{:>20}"
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
            log_chans.append((tx.sensors.items()[0][1].log_chan, tx_id))
            
        log_chans.sort()
        return log_chans
        
    def _listen_for_new_tx(self):
        self.nanode.clear_serial()
        WAIT_TIME = 30
        print("Listening for transmitters for 30 seconds...")
        end_time = time.time() + WAIT_TIME
        while time.time() < end_time:
            data = self._read_sensor_data()
            if not data: # emtpy line suggests timeout
                print("No transmitters heard.")
                return
                
            # Handle data from Nanode
            if data.is_pairing_request:
                if self._user_accepts_pairing(data):
                    print("Pairing with transmitter...")
                    self._handle_pair_request(data)
                    break
            elif data.tx_id not in self.transmitters:
                if self._user_accepts_pairing(data):
                    print("Adding transmitter...")
                    self._add_transmitter(data.tx_id, data.tx_type)
                    self.transmitters[data.tx_id].add_to_nanode()
                    self.transmitters[data.tx_id].update_name(data.sensors)
                    self._pickle()
                    break

    def _handle_pair_request(self, data):
        if data.tx_id in self.transmitters.keys():
            print("Pair request received from a TX we already know")
            self.transmitters[data.tx_id].reject_pair_request()
        else:
            self._add_transmitter(data.tx_id, data.tx_type)
            self.transmitters[data.tx_id].accept_pair_request()
            self._pickle()

    def _add_transmitter(self, tx_id, tx_type):
        self.transmitters[tx_id] = Cc_tx(tx_id, self) if tx_type.lower()=="tx" \
                                   else Cc_trx(tx_id, self)
        
    def _pickle(self):
        with open(Manager.PICKLE_FILE, "wb") as output:
            # "with" ensures we close the file, even if an exception occurs.
            pickle.dump(self.transmitters, output)
                                
    def _user_accepts_pairing(self, data):
        if data.is_pairing_request:
            return yes_no_cancel("Pair request received from {}. Accept? Y/n/c: "
                                       .format(data.tx_id))
        else:
            return yes_no_cancel("Unknown transmitter {} with sensors {}. Add? Y/n/c: "
                                       .format(data.tx_id, 
                                               data.sensors))
    
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
        