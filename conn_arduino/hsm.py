import serial

class HSM:
    charset = 'utf-8'
    opcode_delimiter = '_'
    opcode = {
        'encrypt': 'ENC',
        'decrypt': 'DEC',
        'ping': 'ATT',
        'status': 'STA',
        'setkey': 'SET',
        'setiv': 'SIV',
        'reset': 'RES'
    }

    def __init__(self, device, baudrate, timeout):
        self.device = serial.Serial(port=device, baudrate=baudrate, timeout=timeout)

    def operation(self, opcode, data):
        if type(data) != bytes:
            data = bytes(data, encoding=self.charset)

        payload = bytes(opcode + self.opcode_delimiter, encoding=self.charset) + data
        self.device.write(payload)
        buffer = b''

        while True:
            buffer += self.device.read(size=1)
            self.device.read_until

            if str(buffer).find(opcode + self.opcode_delimiter) > 0:
                buffer = b''

                while True:
                    buffer += self.device.read(size=1)
                    if str(buffer).find(self.opcode_delimiter + opcode) > 0:
                        buffer = buffer[:-1 * len(opcode) - 1]
                        break
                break

        return buffer
    
    def encrypt(self, data):
        result = self.operation(opcode=self.opcode['encrypt'], data=data)

        return result
    
    def decrypt(self, data):
        result = self.operation(opcode=self.opcode['decrypt'], data=data)

        return result