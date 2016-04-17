import logging
from . import machine, idlist

class Universe(object):
    logger = logging.getLogger(__name__)

    PLAYER_SERVICES = [
        'fs',
        'sys',
    ]
    
    def __init__(self):
        self.tickers = idlist.IdList(idlist.integer_id_generator(1337))
        self.machines = idlist.IdList(idlist.random_string_id_generator())

        test_machine = machine.Machine(self, 'test')
        self.machines['test'] = test_machine
        test_machine.start_builtin_service('fs')
    
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

    def create_player_machine(self):
        mach = self.create_machine()
        for svc in self.PLAYER_SERVICES:
            mach.start_builtin_service(svc)
        return mach
        
