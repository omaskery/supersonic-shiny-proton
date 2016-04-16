

from ..opcode import Opcode
from ..instruction import Instruction

import msgpack


def load_program(filehandle):
	unpacker = msgpack.Unpacker(filehandle, encoding='utf8')
	program = []

	while True:
		try:
			inst = Instruction.from_unpacker(unpacker)
		except msgpack.OutOfData:
			break
		program.append(inst)

	return program


class EmulatorState:
	HALTED = 0
	RUNNING = 1
	BLOCKED = 2

	@classmethod
	def from_string(cls, string):
		return {
			'HALTED': cls.HALTED,
			'RUNNING': cls.RUNNING,
			'BLOCKED': cls.BLOCKED,
		}[string.upper()]

	@classmethod
	def to_string(cls, integer):
		return {
			cls.HALTED: 'HALTED',
			cls.RUNNING: 'RUNNING',
			cls.BLOCKED: 'BLOCKED',
		}[integer]



class BlockingReason:
	SEND_RESP = 0
	RECV = 1
	LISTEN = 2

	@classmethod
	def from_string(cls, string):
		return {
			'SEND_RESP': cls.SEND_RESP,
			'RECV': cls.RECV,
			'LISTEN': cls.LISTEN,
		}[string.upper()]

	@classmethod
	def to_string(cls, integer):
		return {
			cls.SEND_RESP: 'SEND_RESP',
			cls.RECV: 'RECV',
			cls.LISTEN: 'LISTEN',
		}[integer]


class Emulator(object):

	def __init__(self, boot_addr=0):
		self._stack = []
		self._program = []
		self._inst_ptr = boot_addr
		self._boot_addr = boot_addr
		self._state = EmulatorState.HALTED
		self._block_reason = None

		self._on_error = None
		self._on_halt = None
		self._on_send = None
		self._on_block = None

	def hook_error(self, handler):
		self._on_error = handler

	def hook_halted(self, handler):
		self._on_halt = handler

	def hook_send(self, handler):
		self._on_send = handler

	def hook_block(self, handler):
		self._on_block = handler

	def trigger_error(self, info):
		self.halt()
		if self._on_error is not None:
			self._on_error(self, info)

	def set_program(self, program):
		self._program = program

	def resume(self):
		self._blocking_reason = None
		self._state = EmulatorState.RUNNING

	def receive(self, sender, values):
		receive_reasons = (
			BlockingReason.SEND_RESP,
			BlockingReason.RECV,
			BlockingReason.LISTEN,
		)

		if self._blocking_reason not in receive_reasons:
			print("receive dropped (block state: {})".format(
				self._blocking_reason
			))
			return

		print("received {} from {}".format(values, sender))
		self._push(sender)
		self._push(values)

		self.resume()

	def halt(self):
		if not self.halted:
			self._state = EmulatorState.HALTED
			if self._on_halt is not None:
				self._on_halt(self)

	@property
	def halted(self):
		return self._state == EmulatorState.HALTED

	@property
	def running(self):
		return self._state == EmulatorState.RUNNING
	
	@property
	def blocked(self):
		return self._state == EmulatorState.BLOCKED

	@property
	def blocking_reason(self):
		return self._block_reason

	def reset(self):
		self.halt()
		self._blocking_reason = None
		self._stack.clear()
		self._inst_ptr = self._boot_addr

	def single_step(self):
		if self.halted or self.blocked:
			return

		if self._inst_ptr < 0 or self._inst_ptr >= len(self._program):
			self.trigger_error("inst ptr exceeded program memory")
			return

		inst = self._program[self._inst_ptr]
		handler = InstructionSet.MAPPING.get(inst.opcode, None)

		if handler is None:
			name = Opcode.to_string(inst.opcode)
			if name is not None:
				self.trigger_error("unimplemented opcode {} at {}".format(
					name, self._inst_ptr
				))
			else:
				self.trigger_error("unknown opcode {} at {}".format(
					inst.opcode, self._inst_ptr
				))
			return

		fn = handler[0]
		extra = handler[1:]
		arguments = tuple([self, inst] + list(extra))

		print("[{}] executing: {}".format(self._inst_ptr, inst))
		fn(*arguments)

	def many_step(self, n):
		for _ in range(n):
			self.single_step()

	def run(self):
		while True:
			self.single_step()

	def _advance_inst(self, n=1):
		if len(self._program) > 0:
			if self._inst_ptr < len(self._program) - 1:
				self._inst_ptr += 1
			else:
				self.halt()
		else:
			self._inst_ptr = 0

	def _push(self, value):
		self._stack.append(value)

	def _pop(self, n=1, preserve_order=False, collapse_single=True):
		if len(self._stack) < n:
			self.trigger_error(
				"attempted to pop {} with only {} on stack at {}".format(
					n, len(self._stack), self._inst_ptr
				)
			)
			return None
		result = self._stack[-n:]
		self._stack = self._stack[:-n]
		if not preserve_order:
			result.reverse()
		if n == 1 and collapse_single:
			result = result[0]
		return result

	def _send(self, target, values, block):
		if block:
			self._block(BlockingReason.SEND_RESP)
		if self._on_send is not None:
			self._on_send(self, target, values)
	
	def _block(self, reason):
		self._blocking_reason = reason
		self._state = EmulatorState.BLOCKED
		if self._on_block is not None:
			self._on_block(self, reason)

	@staticmethod
	def _inst_nop(emu, inst):
		emu._advance_inst()

	@staticmethod
	def _inst_push(emu, inst):
		if len(inst.parameters) != 1:
			emu.trigger_error("push at {} expected 1 argument, got {}".format(
				emu._inst_ptr, len(inst.parameters)
			))
		else:
			emu._push(inst.parameters[0])
			emu._advance_inst()

	@staticmethod
	def _inst_send(emu, inst, block):
		if len(inst.parameters) == 1:
			count = inst.parameters[0]
			if not isinstance(count, int):
				emu.trigger_error(
					"send with 1 argument expects an integer argument"
				)
				return
			values = emu._pop(count, preserve_order=True, collapse_single=False)
			if values is None:
				return
			def _as_list(x):
				if isinstance(x, list):
					return x
				else:
					return [x]
			values = sum(map(_as_list, values), [])
			target = values[0]
			to_send = values[1:]
		elif len(inst.parameters) == 0:
			values = emu._pop()
			if not isinstance(values, list):
				emu.trigger_error(
					"paramaterless send expects a list on top of the stack"
				)
				return
			if len(values) < 1:
				emu.trigger_error(
					"parameterless send expects list to have at least one value with the target in"
				)
				return
			target = values[0]
			to_send = values[1:]
		else:
			emu.trigger_error("send at {} expected 1 argument, got {}".format(
				emu._inst_ptr, len(inst.parameters)
			))
			return
		emu._send(target, to_send, block)
		emu._advance_inst()

	@staticmethod
	def _inst_swap(emu, inst):
		if len(emu._stack) >= 2:
			temp = emu._stack[-1]
			emu._stack[-1] = emu._stack[-2]
			emu._stack[-2] = temp
		else:
			emu.trigger_error("swap at {} had stack <2 big".format(
				emu._inst_ptr
			))
			return
		emu._advance_inst()


class InstructionSet:
	MAPPING = {
		Opcode.NOP: (Emulator._inst_nop,),
		Opcode.PUSH: (Emulator._inst_push,),
		Opcode.SEND: (Emulator._inst_send, True),
		Opcode.SENDI: (Emulator._inst_send, False),
		Opcode.SWAP: (Emulator._inst_swap,),
	}

