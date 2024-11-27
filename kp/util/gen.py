import random
import string

# includes uppercase letters, lowercase letters, and digits
CHARS = string.ascii_lowercase + string.digits


def gen_characters(length: int):
    random_string = ''.join(random.choice(CHARS) for _ in range(length))
    return random_string
