from __future__ import print_function
from __future__ import division
from nanode import Nanode
from transmitter import *


class ManagerError(Exception):
    """Simple class for Manager Errors"""


class Manager(object):
    def __init__(self, nanode):
        self.nanode = nanode
        self.txs  = {}
        self.trxs = {}
        
        # TODO: if radio_ids exists then open it and load data, tell Nanode
        #       how many TXs and TRXs there are and then inform Nanode of
        #       each TX and TRX.

        
    def run(self):
        while True:
            json_line = self.nanode.readjson() 
            
            # Handle data from Nanode
            if json_line.get("pr"): # pair request
                self._handle_pair_request(json_line.get("pr"))
            else:
                print(json_line.get("t"), json_line.get("id"), json_line.get("sensors").get("0"))  
    
    def _handle_pair_request(self, pr):
        tx_type = pr["type"]
        tx_id   = pr["id"]
        if tx_type=="tx":
            if tx_id in self.txs.keys():
                print("Pair request received from a TX we already know")
            else:
                self._pair_with(self.txs, "TX", tx_id)
        else: # tx_type=="trx"
            if tx_id in self.trxs.keys():
                print("Pair request received from a TRX we already know")
                self.nanode.send_command("pw", tx_id)
                self.nanode.send_command("R", tx_id) # remove
            else:
                self._pair_with(self.trxs, "TRX", tx_id)

    def _pair_with(self, d, name, tx_id):
        print("Pairing with", name, tx_id)
        self.nanode.send_command("p", tx_id)
        json_line = self.nanode.readjson()
        if json_line.get("pw").get("id") != tx_id:
            raise ManagerError("Failed to pair with", name, tx_id)
        else:
            print("Successfully paired with", name, tx_id)
        d[tx_id] = Transmitter()
        # TODO: ask for names of sensors


def main():
    print("rfm_ecomanager_logger")
    nanode = Nanode()
    manager = Manager(nanode)
    manager.run()
    
if __name__ == "__main__":
    main()