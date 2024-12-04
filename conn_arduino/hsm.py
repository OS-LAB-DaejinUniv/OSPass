from Crypto.Cipher import AES
import binascii

class HSM:
    return_types = ['hex_string', 'bytes']
    
    def __init__(self, device, baudrate, timeout, return_type = 'hex_string'):
        key = binascii.unhexlify('9A537F1C7A46106FBF7FE3D41BD9D763')
        iv  = binascii.unhexlify('00000000000000000000000000000000')
        
        self.aes_dec = AES.new(key, AES.MODE_CBC, iv)
        self.aes_enc = AES.new(key, AES.MODE_CBC, iv)

        self.return_type = return_type.lower()
        if self.return_type not in self.return_types:
            raise Exception('Unknown return_type')
      
    def encrypt(self, data):
        result = self.aes_enc.encrypt(data)

        return result
    
    def decrypt(self, data):
        try:
            decrypted = self.aes_dec.decrypt(data)
            session_info = {
                'response': binascii.hexlify(decrypted[0:16]),
                'card_uuid': binascii.hexlify(decrypted[16:32]),
                'user_conf': binascii.hexlify(decrypted[32:48])
            }

            if self.return_type == 'hex_string':
                for item in session_info:
                    session_info[item] = session_info[item].decode().upper()

                return session_info

            elif self.return_type == 'bytes':
                return session_info

        except Exception as e:
            print(e)
            return False