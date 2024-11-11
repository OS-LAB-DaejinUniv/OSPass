import sys 
sys.path.append('/home/ubuntu/OS_2FA/')
import const
import serial.tools.list_ports as sp
from .hsm import HSM

SERIAL_NUM = const.SERIAL_NUM
device_path = None
baudurate = 115200
ports = sp.comports()

for i in ports:
    if i.serial_number == SERIAL_NUM:
        device_path = i.device

if device_path is not None:
    print(f'Device Path: {device_path}')
else:
    print(f'NOT FOUND HSM OR DISCONNECTED')

conn_hsm = HSM(device=device_path,baudrate=baudurate,timeout=.1)
