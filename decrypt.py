import os
import binascii
from Crypto.Cipher import AES

secret = binascii.unhexlify(os.getenv("OSLABID_SECRET"))
iv = binascii.unhexlify(os.getenv("OSLABID_IV"))

def decrypt(data):
    cipher = AES.new(secret, AES.MODE_CBC, iv)
    return cipher.decrypt(data)

def decrypt_pp(data):
    decrypted = None

    if type(data) == str and len(data) == 48 * 2:
        data = binascii.unhexlify(data)
        decrypted = decrypt(data)
    
    elif type(data) == bytes and len(data) == 48:
        decrypted = decrypt(data)

    else:
        raise ValueError("Invalid data type or length")
    
    return {
        'response': decrypted[:16].hex().upper(),
        'card_uuid': decrypted[16:32].hex().upper()
    }