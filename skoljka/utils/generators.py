import os
import random
import string


class SimpleKeyGen(object):
    @classmethod
    def generate(cls, length=20):
        return os.urandom(length)


class HexKeyGen(object):
    @classmethod
    def generate(cls, length=20):
        return ''.join([random.choice(string.hexdigits) for i in range(length)])


class AlphaNumKeyGen(object):
    @classmethod
    def generate(cls, length=20):
        alpha_num = string.ascii_letters + string.digits
        return ''.join([random.choice(alpha_num) for i in range(length)])


class LowerNumKeyGen(object):
    @classmethod
    def generate(cls, length=20):
        char_set = string.ascii_lowercase + string.digits
        return ''.join([random.choice(char_set) for i in range(length)])


class SecretKeyGen(AlphaNumKeyGen):
    pass
