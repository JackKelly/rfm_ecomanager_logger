from __future__ import print_function
from transmitter import Cc_tx, Cc_trx
import pickle

class Manager(object):
    """ 
    Attributes:
      - nanode (Nanode)
      - txs  (dict of Transmitters)
      - trxs (dict of Transmitters)
      
    """
    
    PICKLE_FILE = "radioIDs.pkl"
    
    def __init__(self, nanode, args):
        self.transmitters = {}
        self.nanode = nanode
        self.args = args

        # if radio_ids exists then open it and load data, tell Nanode
        # how many TXs and TRXs there are and then inform Nanode of
        # each TX and TRX.
        try:
            pkl_file = open(Manager.PICKLE_FILE, "rb")
        except:
            pass
        else:
            self.transmitters = pickle.load(pkl_file)
            pkl_file.close()
            
            num_txs = 0
            num_trxs = 0
            for dummy, tx in self.transmitters.iteritems():
                tx.manager = self
                if isinstance(tx, Cc_tx):
                    num_txs += 1
                else:
                    num_trxs += 1
            
            self.nanode.send_command('s', num_txs)
            self.nanode.send_command('S', num_trxs)
            
            for dummy, tx in self.transmitters.iteritems():
                tx.add_to_nanode()

    def run(self):
        while True:
            json_line = self.nanode.readjson() 
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
    
