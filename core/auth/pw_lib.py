from pwdlib import PasswordHash

pw_lib = PasswordHash.recommended()


def hash_password(plain_password):
    return pw_lib.hash(plain_password)


def verify_hash(hash, password):
    return pw_lib.verify(password, hash)
