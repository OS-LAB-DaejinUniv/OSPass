import os
import binascii
from Crypto.Cipher import AES
from dotenv import load_dotenv
from custom_log import LoggerSetup

load_dotenv()

logger_setup = LoggerSetup()
logger = logger_setup.logger

secret = iv = None 

secret_hex_env = os.getenv("OSLABID_SECRET") 
iv_hex_env = os.getenv("OSLABID_IV")         

logger.debug(f"Loaded SECRET env var (RAW): '{secret_hex_env}'") 
logger.debug(f"Loaded IV env var (RAW): '{iv_hex_env}'")         

try:
    if secret_hex_env:
        secret = binascii.unhexlify(secret_hex_env) 
        logger.debug(f"Unhexlified SECRET (Bytes HEX): {secret.hex().upper()}") 
        logger.debug(f"Unhexlified SECRET Length: {len(secret)}") 
    else:
         logger.error("OSLABID_SECRET environment variable is not set!")

    if iv_hex_env:
        iv = binascii.unhexlify(iv_hex_env)        
        logger.debug(f"Unhexlified IV (Bytes HEX): {iv.hex().upper()}")         
        logger.debug(f"Unhexlified IV Length: {len(iv)}")
    else:
         logger.error("OSLABID_IV environment variable is not set!")
         
except binascii.Error as e:
     logger.error(f"binascii.unhexlify Error for Key/IV: {e}. Ensure env vars are valid HEX strings.")
     
except Exception as e:
    logger.error(f"Unexpected Error during Key/IV loading: {e}")
    
     
def decrypt(data):
    
    if secret is None or iv is None:
         logger.error("Attempting decrypt but Key or IV was not loaded correctly!")
         
         raise ValueError("Encryption system not initialized: Missing Key or IV")

    
    expected_key_length = 16 
    expected_iv_length = 16 
    
    if len(secret) != expected_key_length or len(iv) != expected_iv_length:
         logger.error(f"Invalid Key or IV length for AES mode. Expected Key {expected_key_length}, IV {expected_iv_length}. Got Key {len(secret)}, IV {len(iv)}")
         
         raise ValueError(f"Encryption Key/IV length mismatch. Expected Key {expected_key_length}, got {len(secret)}. Expected IV {expected_iv_length}, got {len(iv)}")

    logger.debug(f"DEBUG: Actual Key Bytes Used for AES (HEX): {secret.hex().upper()}")
    logger.debug(f"DEBUG: Actual IV Bytes Used for AES (HEX): {iv.hex().upper()}")
    
    try:
        cipher = AES.new(secret, AES.MODE_CBC, iv) 
        return cipher.decrypt(data)
    except ValueError as e:
        
        logger.error(f"PyCryptodome AES.new failed: {e}. Key len: {len(secret)}, IV len: {len(iv)}")
        raise ValueError("Failed to initialize decryption cipher") from e
    except Exception as e:
         logger.error(f"Unexpected error during AES decryption: {e}")
         raise 

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