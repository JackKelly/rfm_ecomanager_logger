from __future__ import print_function
from transmitter import Cc_tx, Cc_trx
import pickle
from nanode import NanodeRestart
from input_with_quit import Quit

class Manager(object):
    """ 
    Attributes:
      - nanode (Nanode)
      - txs  (dict of Transmitters)
      - trxs (dict of Transmitters)
      
    """
    
    PICKLE_FILE = "radioIDs.pkl"
    
    def __init__(self, nanode, args):
        self.nanode = nanode
        self.args = args

        # if radio_ids exists then open it and load data, tell Nanode
        # how many TXs and TRXs there are and then inform Nanode of
        # each TX and TRX.
        try:
            pkl_file = open(Manager.PICKLE_FILE, "rb")
        except:
            self.transmitters = {}
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
            self.nanode.send_command('s', num_txs)
            self.nanode.send_command('S', num_trxs)       
            for dummy, tx in self.transmitters.iteritems():
                tx.add_to_nanode()

    def run_logging(self):
        while True:
            try:
                json_line = self.nanode.readjson()
            except NanodeRestart:
                self.nanode.send_init_commands()
                self._tell_nanode_about_transmitters()
            else:
                if json_line:
                    tx_id = json_line.get("id")
                    if tx_id in self.transmitters:
                        self.transmitters[tx_id] \
                            .new_reading(json_line.get("sensors"))
    
    def _process_json(self, json_line):
        if not json_line:
            return
        
        tx_id = json_line.get("id")
            
        # Handle data from Nanode
        if json_line.get("pr"): # pair request
            self._handle_pair_request(json_line.get("pr"))
        else:
            if tx_id in self.transmitters:
                self.transmitters[tx_id] \
                    .new_reading(json_line.get("sensors"))
            elif self.args.promiscuous:
                self._add_transmitter(tx_id, json_line.get("type"))
                self.transmitters[tx_id].add_to_nanode()
                self.transmitters[tx_id].update_name(json_line.get("sensors"))
                self.pickle()

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
    
    def _handle_pair_request(self, pr):
        tx_id  = pr["id"]
        if tx_id in self.transmitters.keys():
            print("Pair request received from a TX we already know")
            self.transmitters[tx_id].reject_pair_request()
        else:
            self._add_transmitter(tx_id, pr["type"])
            self.transmitters[tx_id].accept_pair_request()
            self.pickle()

    def _add_transmitter(self, tx_id, tx_type):
        self.transmitters[tx_id] = Cc_tx(tx_id, self) if tx_type=="tx" \
                                   else Cc_trx(tx_id, self)
        
    def pickle(self):
        output = open(Manager.PICKLE_FILE, "wb")
        pickle.dump(self.transmitters, output)
        output.close()

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
    
    def run_training(self):
        while True:
            cmd = raw_input("Enter command (or ? for help): ")
            if cmd == "?":
                print("")
                print("l      : list all known transmitters")
                print("n      : listen for new transmitter (not in pairing mode)")
                print("p      : pair with new transmitter in pairing mode")
                print("m      : manually enter transmitter ID")
                print("<index>: edit known transmitter")
                print("q      : quit")
                print("")
            elif cmd == "l": self._list_transmitters()
            elif cmd == "n": self._listen_for_new_tx()
            elif cmd == "p": self._pair_with_new_tx()
            elif cmd == "m": self._manually_enter_id()
            elif cmd.isdigit(): self._edit_transmitter(cmd)
            elif cmd == "q":
                print("quit\n") 
                break
            else:
                print("Unrecognised command: '{}'\n".format(cmd))

    def _list_transmitters(self):
        print("")
        print("{:5s}{:>12s}{:>6}{:>8}{:>10}{:>15}"
              .format("INDEX", "RF_ID", "TYPE", "SENSOR", "LOG_CHAN", "NAME"))

        log_chans = self._get_log_chans_and_rf_ids()
        for log_chan, tx_id in log_chans:
            print("{:>5d}{:>12d}{:>6}{}"
                  .format(log_chan, tx_id, self.transmitters[tx_id].TYPE
                          , self.transmitters[tx_id].print_sensors()))
        print("")
    
    
    def _edit_transmitter(self, cmd):
        try:
            target_log_chan = int(cmd)
        except ValueError:
            print(cmd, "is not an int. Please try again.\n")
            return
        
        log_chans = self._get_log_chans_and_rf_ids()
        target_tx_id = None
        for log_chan, tx_id in log_chans:
            if log_chan == target_log_chan:
                target_tx_id = tx_id
                break
        
        if not target_tx_id:
            print(cmd, "could not be found. Please try again.\n")
            return
        
        try:
            self.transmitters[target_tx_id].update_name()
        except Quit:
            pass
        else:
            self.pickle()
            print("")
        
    
    def _get_log_chans_and_rf_ids(self):
        log_chans = []
        for tx_id, tx in self.transmitters.iteritems():
            log_chans.append((tx.sensors[1].log_chan, tx_id))
            
        log_chans.sort()
        return log_chans
        
