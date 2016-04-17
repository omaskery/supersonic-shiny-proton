import ssp.scripting.emulator
emu = ssp.scripting.emulator

class Process(object):
    """
    Base class for all processes (emulated or virtual).
    """

    def __init__(self, machine, pid, ppid):
        self.logger = machine.logger.getChild('processes.{}'.format(pid))
        self.machine = machine
        self.pid = pid
        self.ppid = ppid
        self.logger.debug('new process: ppid={}'.format(ppid))

class EmuProcess(Process):
    STATE_IDLE = 0
    STATE_RUNNING = 1
    STATE_BLOCKED = 2
    
    def __init__(self, machine, pid, ppid):
        super(EmuProcess, self).__init__(machine, pid, ppid)

        self.emu = emu.Emulator(verbose=100)
        self.emu.hook_error(self._on_error)
        self.emu.hook_halted(self._on_halted)
        self.emu.hook_send(self._on_send)
        self.emu.hook_block(self._on_block)
        self.emu.hook_resume(self._on_resume)

    def _on_error(self, emu, err, addr):
        self.logger.error("error[0x{:04X}]: {}".format(addr, err))

    def _on_halted(self, emu):
        self.logger.info("halted")
                
    def _on_send(self, emu, target, values):
        if target == ".":
            target = self.ppid

        self.logger.info("sending:", values, "to", target)
        
        try:
            ret = self.machine.send_ipc(self, target, values)
            emu.receive(target, ret)
        except Exception as e:
            emu.trigger_error('error sending: {}'.format(repr(e)))
        
    def _on_block(self, e, reason):
        self.logger.debug("blocked on", emu.BlockingReason.to_string(reason))
        self.machine.unregister_tick(self.tick_id)

    def _on_resume(self, e):
        self.tick_id = self.machine.register_tick(self._on_tick)

    def _on_tick(self):
        self.emu.single_step()

    def send_ipc(self, sender, values):
        self.logger.debug('receive {}, {}'.format(sender, values))
        self.emu.receive(sender, values)

    def run_program(self, program):
        if self.emu.state == emu.EmulatorState.HALTED:
            self.emu.set_program(program)
            self.emu.resume()
