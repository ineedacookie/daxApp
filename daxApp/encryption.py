import base64
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from daxApp.settings import ENCRYPT_CODE

# Generate a salt
salt = b'fndmentalSaltIsUsed'


kdf = PBKDF2HMAC(
    algorithm=hashes.SHA256(),
    length=32,
    salt=salt,
    iterations=4    # 10000 is recommend for non sensitive data, but considering that I am not sharing the key outside of the application at the moment I am not concerned about someone breaking it.
)
key = base64.urlsafe_b64encode(kdf.derive(ENCRYPT_CODE))
FERNET = Fernet(key)


# Encrypt the ID
def encrypt_id(in_id):
    return FERNET.encrypt(bytes(str(in_id), 'utf-8')).decode()


# Decrypt the ID
def decrypt_id(in_id):
    return int(FERNET.decrypt(bytes(in_id, 'utf-8')).decode())
