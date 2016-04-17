import logging
from . import machine, idlist

class Universe(object):
    logger = logging.getLogger(__name__)
    
    def __init__(self):
        self.tickers = idlist.IdList(idlist.integer_id_generator(1337))
        self.machines = idlist.IdList(idlist.random_string_id_generator())
    
    def tick(self):
        for v in list(self.tickers.values()):
            v()

    def register_tick(self, cb):
        return self.tickers.add(cb)

    def unregister_tick(self, id):
        del self.tickers[id]

    def create_machine(self, ctor=machine.Machine):
        id = self.machines.add_fn(lambda id: ctor(self, id))
        machine = self.machines[id]
        return machine
        
