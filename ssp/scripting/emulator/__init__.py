

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

	def __init__(self, boot_addr=0, verbose=0):
		self._stack = []
		self._program = []
		self._inst_ptr = boot_addr
		self._boot_addr = boot_addr
		self._state = EmulatorState.HALTED
		self._block_reason = None
		self._verbose = verbose
		self._cycles = 0

		self._on_error = None
		self._on_halt = None
		self._on_send = None
		self._on_block = None
		self._on_resume = None

	@property
	def state(self):
		return self._state

	def hook_error(self, handler):
		self._on_error = handler

	def hook_halted(self, handler):
		self._on_halt = handler

	def hook_send(self, handler):
		self._on_send = handler

	def hook_block(self, handler):
		self._on_block = handler
		
	def hook_resume(self, handler):
		self._on_resume = handler

	def trigger_error(self, info):
		self.halt()
		if self._on_error is not None:
			self._on_error(self, info, self._inst_ptr)

	def set_program(self, program):
		self._program = program

	def resume(self):
		print('resume {} {}'.format(self._state, self._on_resume))
		if (self._state != EmulatorState.RUNNING) and (self._on_resume is not None):
			self._on_resume(self)
	
		self._blocking_reason = None
		self._state = EmulatorState.RUNNING

	def receive(self, sender, values):
		receive_reasons = (
			BlockingReason.SEND_RESP,
			BlockingReason.RECV,
			BlockingReason.LISTEN,
		)

		if self._blocking_reason not in receive_reasons:
			if self._verbose:
				print("receive dropped (block state: {})".format(
					self._blocking_reason
				))
			return

		if self._verbose:
			print("received {} from {}".format(values, sender))
		# pushing values first and sender last on the assumption that
		# you will more often want to discard the sender than the values
		# so it is more ergonomic to do "POP" than "SWAP; POP"
		self._push(values)
		self._push(sender)

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
		self._cycles = 0

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
				self.trigger_error("unimplemented opcode {}".format(
					name
				))
			else:
				self.trigger_error("unknown opcode {}".format(
					inst.opcode
				))
			return

		fn = handler[0]
		extra = handler[1:]
		arguments = tuple([self, inst] + list(extra))

		if self._verbose:
			print("[0x{:04X}] executing: {}".format(self._inst_ptr, inst))
		fn(*arguments)
		if self._verbose > 1:
			print("stack:", ", ".join(map(str, self._stack)))

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

	def _jump(self, addr):
		if 0 <= addr < len(self._program):
			self._inst_ptr = addr
		else:
			self.trigger_error("attempted to jump out of bounds: {}".format(addr))

	def _push(self, value):
		self._stack.append(value)

	def _pop(self, n=1, preserve_order=False, collapse_single=True):
		if len(self._stack) < n:
			self.trigger_error(
				"attempted to pop {} with only {} on stack".format(
					n, len(self._stack)
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
			emu.trigger_error("push expected 1 argument, got {}".format(
				len(inst.parameters)
			))
		else:
			emu._push(inst.parameters[0])
			emu._advance_inst()

	@staticmethod
	def _inst_send(emu, inst, block):
		if len(inst.parameters) == 1:
			values = inst.parameters[0]
		elif len(inst.parameters) == 0:
			values = emu._pop()
			if values is None: return
		else:
			emu.trigger_error("send expected 0 or 1 arguments, got {}".format(
				len(inst.parameters)
			))
			return
		if not isinstance(values, list):
			emu.trigger_error(
				"send expects a list as only parameter or on top of the stack"
			)
			return
		if len(values) < 1:
			emu.trigger_error(
				"send expects value list to have at least one value with the target in"
			)
			return
		target = values[0]
		to_send = values[1:]
		emu._send(target, to_send, block)
		emu._advance_inst()

	@staticmethod
	def _inst_swap(emu, inst):
		if len(emu._stack) >= 2:
			temp = emu._stack[-1]
			emu._stack[-1] = emu._stack[-2]
			emu._stack[-2] = temp
		else:
			emu.trigger_error("swap had stack <2 big")
			return
		emu._advance_inst()

	@staticmethod
	def _inst_append(emu, inst):
		if len(inst.parameters) == 0:
			pop_count = emu._pop()
			if pop_count is None: return
		elif len(inst.parameters) == 1:
			pop_count = inst.parameters[0]
		else:
			emu.trigger_error("append requires one integer pop count argument")
			return
		
		if not isinstance(pop_count, int):
			emu.trigger_error("append expects a single integer pop count")
			return

		values = emu._pop(pop_count, preserve_order=True, collapse_single=False)
		if values is None:
			return

		top = emu._pop()
		if not isinstance(top, list):
			emu.trigger_error(
				"append at {} expects top of stack (under args) to be a list"
			)
			return

		top = top + values
		emu._push(top)

		emu._advance_inst()

	@staticmethod
	def _inst_pop(emu, inst):
		count = 1
		if len(inst.parameters) == 0:
			count = emu._pop()
			if count is None: return
		elif len(inst.parameters) == 1:
			count = inst.parameters[0]
		else:
			emu.trigger_error("pop can only accept 0 or 1 arguments, not {}".format(
				len(inst.parameters)
			))
			return
		if not isinstance(count, int):
			emu.trigger_error("pop count must be an integer")
			return
		emu._pop(count)
		emu._advance_inst()

	@staticmethod
	def _inst_binop(emu, inst, op_fn):
		values = emu._pop(2, preserve_order=True, collapse_single=False)
		if values is None:
			return

		for index, value in enumerate(values):
			if not isinstance(value, (int, float)):
				emu.trigger_error("arg {} (#{}) is not an integer or float".format(
					value, index
				))
				return

		if len(values) != 2:
			emu.trigger_error("{} cannot operate on more than 2 operands".format(
				Opcode.to_string(inst.opcode)
			))
			return
		result = op_fn(values[0], values[1])
		
		emu._push(result)
		emu._advance_inst()

	@staticmethod
	def _inst_dict(emu, inst):
		if len(inst.parameters) == 0:
			pair_count = emu._pop()
			if pair_count is None: return
		elif len(inst.parameters) == 1:
			pair_count = inst.parameters[0]
		else:
			emu.trigger_error("dict expects 0 or 1 arguments, not {}".format(
				len(inst.parameters)
			))
			return

		if not isinstance(pair_count, int):
			emu.trigger_error("dict expects an integer parameter")
			return

		values = emu._pop(pair_count * 2, preserve_order=True)
		if values is None:
			return

		result = dict([
			values[i:i+2]
			for i in range(0, len(values), 2)
		])

		emu._push(result)
		emu._advance_inst()

	@staticmethod
	def _inst_put(emu, inst):
		if len(inst.parameters) == 0:
			pair_count = emu._pop()
			if pair_count is None: return
		elif len(inst.parameters) == 1:
			pair_count = inst.parameters[0]
		else:
			emu.trigger_error("put expects 0 or 1 arguments, not {}".format(
				len(inst.parameters)
			))
			return

		if not isinstance(pair_count, int):
			emu.trigger_error("put expects an integer parameter")
			return

		values = emu._pop(pair_count * 2, preserve_order=True)
		if values is None:
			return

		target = emu._pop()
		if target is None:
			return

		if not isinstance(target, dict):
			emu.trigger_error("put expects the stack to contain a dictionary under values")
			return

		updates = dict([
			values[i:i+2]
			for i in range(0, len(values), 2)
		])
		target.update(updates)
		
		emu._advance_inst()

	@staticmethod
	def _inst_dup(emu, inst):
		if len(inst.parameters) == 0:
			offset = emu._pop()
			if offset is None: return
		elif len(inst.parameters) == 1:
			offset = inst.parameters[0]
		else:
			emu.trigger_error("dup expects 0 or 1 arguments, not {}".format(
				len(inst.parameters)
			))
			return

		if not isinstance(offset, int):
			emu.trigger_error("dup expects an integer parameter")
			return

		if offset >= 0:
			emu.trigger_error("dup expects an integer < 0")
			return

		target = emu._stack[offset]
		emu._push(target)
		
		emu._advance_inst()

	@staticmethod
	def _inst_lookup(emu, inst):
		if len(inst.parameters) == 0:
			needle = emu._pop()
			if needle is None: return
		elif len(inst.parameters) == 1:
			needle = inst.parameters[0]
		else:
			emu.trigger_error("lookup expects 0 or 1 arguments, not {}".format(
				len(inst.parameters)
			))
			return

		target = emu._pop()
		if target is None:
			return

		if isinstance(target, list):
			if not isinstance(needle, int):
				emu.trigger_error("lookup argument for list target must be int")
				return
			if 0 <= needle < len(target):
				result = target[needle]
			else:
				emu.trigger_error("lookup argument {} for list out of bounds, len: {}".format(
					needle, len(target)
				))
				return
		elif isinstance(target, dict):
			result = target.get(needle, None)
		else:
			emu.trigger_error("lookup target must be list or dictionary")
			return

		emu._push(result)
		emu._advance_inst()

	@staticmethod
	def _inst_list(emu, inst):
		if len(inst.parameters) == 0:
			count = emu._pop()
			if count is None: return
		elif len(inst.parameters) == 1:
			count = inst.parameters[0]
		else:
			emu.trigger_error("list expects 0 or 1 arguments, not {}".format(
				len(inst.parameters)
			))
			return

		if not isinstance(count, int):
			emu.trigger_error("list expects an integer parameter")
			return

		values = emu._pop(count, preserve_order=True)
		if values is None:
			return

		emu._push(values)
		emu._advance_inst()

	@staticmethod
	def _inst_len(emu, inst):
		target = emu._pop()
		if target is None:
			return

		if not isinstance(target, (list, dict)):
			emu.trigger_error("len expects a list or dictionary target on top of stack")
			return

		emu._push(len(target))
		emu._advance_inst()

	@staticmethod
	def _inst_recv(emu, inst):
		emu._block(BlockingReason.RECV)
		emu._advance_inst()

	@staticmethod
	def _inst_listen(emu, inst):
		emu._block(BlockingReason.LISTEN)
		emu._advance_inst()

	@staticmethod
	def _inst_zero(emu, inst):
		top = emu._pop()
		if top is None: return
		emu._push(top == 0)
		emu._advance_inst()

	@staticmethod
	def _inst_gt(emu, inst):
		top = emu._pop()
		if top is None: return
		emu._push(top > 0)
		emu._advance_inst()

	@staticmethod
	def _inst_lt(emu, inst):
		top = emu._pop()
		if top is None: return
		emu._push(top < 0)
		emu._advance_inst()

	@staticmethod
	def _inst_ji(emu, inst):
		if len(inst.parameters) == 0:
			target = emu._pop()
			if target is None: return
		elif len(inst.parameters) == 1:
			target = inst.parameters[0]
		else:
			emu.trigger_error("ji expects zero or one integer parameters")
			return

		top = emu._pop()
		if top is None: return

		if not isinstance(target, int):
			emu.trigger_error("ji parameter must be of type integer")
			return

		if top:
			emu._jump(target)
		else:
			emu._advance_inst()

	@staticmethod
	def _inst_jn(emu, inst):
		if len(inst.parameters) == 0:
			target = emu._pop()
			if target is None: return
		elif len(inst.parameters) == 1:
			target = inst.parameters[0]
		else:
			emu.trigger_error("jn expects zero or one integer parameters")
			return

		top = emu._pop()
		if top is None: return

		if not isinstance(target, int):
			emu.trigger_error("jn parameter must be of type integer")
			return

		if not top:
			emu._jump(target)
		else:
			emu._advance_inst()

	@staticmethod
	def _binop_add(a, b):
		return a + b

	@staticmethod
	def _binop_sub(a, b):
		return a - b

	@staticmethod
	def _binop_mul(a, b):
		return a * b

	@staticmethod
	def _binop_div(a, b):
		return a / b


class InstructionSet:
	MAPPING = {
		Opcode.NOP: (Emulator._inst_nop,),
		Opcode.PUSH: (Emulator._inst_push,),
		Opcode.SEND: (Emulator._inst_send, True),
		Opcode.SENDI: (Emulator._inst_send, False),
		Opcode.SWAP: (Emulator._inst_swap,),
		Opcode.APPEND: (Emulator._inst_append,),
		Opcode.POP: (Emulator._inst_pop,),
		Opcode.ADD: (Emulator._inst_binop, Emulator._binop_add),
		Opcode.SUB: (Emulator._inst_binop, Emulator._binop_sub),
		Opcode.MUL: (Emulator._inst_binop, Emulator._binop_mul),
		Opcode.DIV: (Emulator._inst_binop, Emulator._binop_div),
		Opcode.DICT: (Emulator._inst_dict,),
		Opcode.PUT: (Emulator._inst_put,),
		Opcode.DUP: (Emulator._inst_dup,),
		Opcode.LOOKUP: (Emulator._inst_lookup,),
		Opcode.LIST: (Emulator._inst_list,),
		Opcode.LEN: (Emulator._inst_len,),
		Opcode.RECV: (Emulator._inst_recv,),
		Opcode.LISTEN: (Emulator._inst_listen,),
		Opcode.ZERO: (Emulator._inst_zero,),
		Opcode.GT: (Emulator._inst_gt,),
		Opcode.LT: (Emulator._inst_lt,),
		Opcode.JI: (Emulator._inst_ji,),
		Opcode.JN: (Emulator._inst_jn,),
	}

