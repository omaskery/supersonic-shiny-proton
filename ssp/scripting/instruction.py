

from .opcode import Opcode
import json


class Instruction(object):

	def __init__(self, opcode, parameters):
		self._opcode = opcode
		self._parameters = parameters

		self._line = 1
		self._col = 1

	@property
	def opcode(self):
		return self._opcode

	@property
	def parameters(self):
		return self._parameters

	@property
	def line(self):
		return self._line

	@property
	def col(self):
		return self._col

	def at(self, line, col):
		self._line = line
		self._col = col
		return self

	def pretty_string(self):
		opcode_str = Opcode.to_string(self._opcode)
		if opcode_str is None:
			opcode_str = "unknown_opcode_0x{:02X}".format(self._opcode)
		tokens = [opcode_str]

		for index, param in enumerate(self.parameters):
			last = index == len(self.parameters) - 1
			if not last:
				param_str = json.dumps(param)
			else:
				param_str = json.dumps(param, indent=4)
			tokens.append(param_str)

		return " ".join(tokens)

	def __str__(self):
		result = "{} ({})".format(Opcode.to_string(self._opcode), self._opcode)
		if len(self._parameters) > 0:
			result += ": " + " ".join(map(str, self._parameters))
		return result

	@staticmethod
	def from_unpacker(unpacker):
		opcode = unpacker.unpack()
		parameters = unpacker.unpack()
		return Instruction(opcode, parameters)

