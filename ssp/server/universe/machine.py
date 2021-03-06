import logging
import string
import weakref
from pyee import EventEmitter

from . import process, idlist, machine_services


def maybe_remote_address(addr):
    if not isinstance(addr, str):
        return None
    
    idx = addr.find(':')
    if idx < 0:
        return None

    return (addr[:idx], addr[idx+1:])

class Machine(object):
    def __init__(self, universe, id):
        self.logger = universe.logger.getChild('machines.{}'.format(id))
        
        self.universe = universe
        self.id = id
        self.secret = idlist.generate_random_id(length=40)
        
        self.processes = idlist.IdList(idlist.integer_id_generator(1000))
        self.services = weakref.WeakValueDictionary()

        self.register_tick = universe.register_tick
        self.unregister_tick = universe.unregister_tick

        self.events = EventEmitter()

    def create_process(self, ppid=None, factory=process.EmuProcess):
        pid = self.processes.add_fn(lambda id: factory(self, id, ppid))
        proc = self.processes[pid]

        self.events.emit('process_created', proc)
        return proc

    def start_process(self, program):
        parent = self.create_process(factory=machine_services.InterfaceService)
        try:
            proc = self.create_process(ppid=parent.pid)
            proc.run_program(program)

            return (proc, parent)
        finally:
            self.kill_process(parent.pid)

    def kill_process(self, pid):
        proc = self.processes.get(pid)
        if proc is None:
            return

        del self.processes[pid]
        self.events.emit('process_killed', proc)
        proc.kill()

    async def interface_send(self, target, values):
        parent = self.create_process(factory=machine_services.InterfaceService)
        try:
            return await self.send_ipc(str(parent.pid), target, values)
        finally:
            self.kill_process(parent.pid)

    def register_service(self, proc, service):
        self.services[service] = proc

    def start_builtin_service(self, svc):
        factory = machine_services.FACTORIES.get(svc)
        if factory is None:
            self.logger.error('tried to start non-existant service: {}'.format(svc))
            return
        
        proc = self.create_process(factory=factory)
        self.register_service(proc, svc)
        return proc

    async def send_ipc(self, sender, target, values):
        addr = maybe_remote_address(target)
        if addr is not None:
            dest = self.universe.machines.get(addr[0])
            if dest is None:
                raise Exception('destination machine {} not found'.format(addr[0]))
            return await dest.send_ipc('{}:{}'.format(self.id, sender), addr[1], values)

        if (len(target) > 0) and (target[0] in string.digits):
            target = int(target)
        
        if target in self.processes:
            return await self.processes[target].send_ipc(sender, values)

        if target in self.services:
            svc = self.services[target]
            if svc is not None:
                return await svc.send_ipc(sender, values)

        raise Exception('no receiver {}'.format(target))
