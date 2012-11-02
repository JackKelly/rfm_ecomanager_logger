from __future__ import print_function
from __future__ import division
import json
import serial

def extract_dict(json_data):
    dict = {}
    for tx in json_data:
        if tx.get("sensors"):
            dict[tx.get("id")] = [None,None,None]
            for sensor in tx.get("sensors"):
                dict[tx.get("id")][sensor.get("s")] = sensor.get("chan")
        else:
            dict[tx.get("id")] = [tx.get("chan")]
            
    return dict
   

def send_dict_to_nanode(dict, tx_type):
    try:
        ser = serial.Serial("/dev/ttyUSB0", 115200)
    except(OSError, serial.SerialException), e:
        print("Serial port error")
        raise
    
    ser.flushInput()
    ser.write("n");
    if ser.readline().split()[0] != 'ACK':
        print("error")
    cmd = "{:d}\r\n".format(33)
    ser.write(cmd);
    echo = ser.readline() # read echo
    response = ser.readline() 
    if response.split()[0] != 'ACK':
        print("error: " + response)
    ser.close()
    

def main():
    json_file = open("radioIDs.json")
    json_data = json.load(json_file)
    json_file.close()

    txs  = extract_dict(json_data.get("TXs"));
    trxs = extract_dict(json_data.get("TRXs"));

    print(txs)
    print(trxs)
    
    send_dict_to_nanode(txs, "TXs")

    
if __name__ == "__main__":
    main()