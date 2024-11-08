import serial.tools.list_ports as sp
import serial
import const

SERIAL_NUM = const.SERIAL_NUM
device_path = None

ports = sp.comports()

for i in ports:
    if i.serial_number == SERIAL_NUM:
        device_path = i.device
        
if device_path is not None:
    print(f'Device Path : {device_path}')
else:
    print(f'NOT FOUND HSM OR DISCONNECTED')
    
###
# Serial을 열고
# 데이터 읽고 쓰기 하면 됨(무슨 데이터? Response~)
###
ser = serial.Serial(device_path, 115200)

ser.write(b'ENC_Hello')

# 복호화 된 Response -> 인가 코드 발급 로직에 전달
async def send_enr_data():
        data = ser.readline()
        print(f"복호화 된 Response: {data}")
        return await data

# TODO: binary code -> string 변환, substring
    

