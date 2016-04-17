import logging
from . import process, idlist

class Machine(object):
    def __init__(self, universe, id):
        self.logger = universe.logger.getChild('machines.{}'.format(id))
        
        self.universe = universe
        self.id = id
        self.secret = idlist.generate_random_id(length=40)
        
        self.processes = idlist.IdList(idlist.integer_id_generator(1000))

        self.register_tick = universe.register_tick
        self.unregister_tick = universe.unregister_tick

    def create_process(self, ppid=None, ctor=process.EmuProcess):
        pid = self.processes.add_fn(lambda id: ctor(self, id, ppid))
        proc = self.processes[pid]
        return proc

    def start_process(self, program):
        proc = self.create_process()
        proc.run_program(program)
        return proc

    def send_ipc(self, sender, target, values):
        sender_id = sender.pid # TODO: prepend address if not local
        
        if target in self.processes:
            return self.processes[target].send_ipc(self, sender, values)

        raise Exception('no receiver')
