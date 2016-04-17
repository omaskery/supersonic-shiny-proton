import random
import string

def integer_id_generator(next_id=0):
    while True:
        yield next_id
        next_id += 1

def generate_random_id(length=20, charset=string.ascii_uppercase + string.digits, rand = random.SystemRandom()):
    return ''.join(rand.choice(charset) for _ in range(length))

def random_string_id_generator(length=20, charset=string.ascii_uppercase + string.digits, rand = random.SystemRandom()):
    while True:
        yield generate_random_id(length, charset, rand)

class IdList(object):
    def __init__(self, id_generator=None):
        if id_generator is None:
            id_generator = integer_id_generator()
        
        self.dict = {}
        self.id_generator = id_generator

    def __getitem__(self, index):
        return self.dict[index]

    def __setitem__(self, index, value):
        self.dict[index] = value

    def __delitem__(self, index):
        del self.dict[index]

    def __contains__(self, index):
        return index in self.dict

    def generate_id(self):
        id = None
        
        while (id is None) or (id in self.dict):
            id = next(self.id_generator)

        return id

    def add(self, value):
        id = self.generate_id()
        self.dict[id] = value
        return id

    def add_fn(self, cb):
        id = self.generate_id()
        value = cb(id)
        self.dict[id] = value
        return id
        
    def remove(self, id):
        del self.dict[id]

    def keys(self):
        return self.dict.keys()

    def values(self):
        return self.dict.values()

    def items(self):
        return self.dict.items()

    def get(self, id, default=None):
        return self.dict.get(id, default)
