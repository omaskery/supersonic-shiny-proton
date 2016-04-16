

from .parser import Parser, Instruction
from .lexer import Lexer, TokenType
from ..opcode import Opcode


from collections import namedtuple
import msgpack


class ErrorLevel:
	WARNING = 0
	ERROR = 1
	INT_ERROR = 2

	@classmethod
	def to_string(cls, integer):
		return {
			cls.WARNING: 'warning',
			cls.ERROR: 'error',
			cls.INT_ERROR: 'internal error',
		}.get(integer, None)


class AssemblerMessage(namedtuple('AssemblerMessage', 'level line col message')):
	
	def __str__(self):
		return "{} [{}:{}]: {}".format(
			ErrorLevel.to_string(self.level), self.line, self.col, self.message
		)


class Assembler(object):

	def __init__(self):
		self._result = []
		self._messages = {
			ErrorLevel.WARNING: [],
			ErrorLevel.ERROR: [],
			ErrorLevel.INT_ERROR: [],
		}

	def assemble(self, source, output):
		lexer = Lexer(source)
		parser = Parser(lexer)

		while True:
			instruction = parser.parse_instruction()

			if instruction is None:
				break

			if instruction.opcode is None:
				self._error(instruction, "unknown opcode")
				continue

			info = Assembler.TYPE_INFO.get(instruction.opcode, None)
			if info is None:
				self._int_error(instruction, "no type info for opcode {}".format(
					Opcode.to_string(instruction.opcode)
				))
				continue
			if len(info) < 1:
				self._int_error(instruction, "malformed type info for opcode {}".format(
					Opcode.to_string(instruction.opcode)
				))
				continue

			max_args = info[0]
			param_types = info[1:]

			if max_args is not None and len(instruction.parameters) > max_args:
				self._error(instruction,
					"too many parameters to opcode {} (max: {})".format(
						Opcode.to_string(instruction.opcode), max_args
					)
				)
				continue

			parameters = []

			bad_types = 0
			for index, (param_type, param_value) in enumerate(instruction.parameters):
				if index < len(param_types):
					expected_types = param_types[index]
				else:
					param_types[-1]
				okay = self._check_parameter(param_type, expected_types)
				if not okay:
					self._error(instruction, "param {} of {} is type {}, valid types: {}".format(
						index + 1, Opcode.to_string(instruction.opcode),
						TokenType.to_type_name(param_type),
						", ".join(map(TokenType.to_type_name, expected_types))
					))
					bad_types += 1
				parameters.append(param_value)
			if bad_types > 0:
				continue

			self._emit(instruction.opcode, *parameters)

		errors = self.all_errors

		if len(errors) == 0:
			self._write_result(output)

		return self.warnings + errors

	def get_message_counts(self):
		return len(self.warnings), len(self.errors), len(self.internal_errors)

	@property
	def warnings(self):
		return self._messages[ErrorLevel.WARNING]

	@property
	def errors(self):
		return self._messages[ErrorLevel.ERROR]

	@property
	def internal_errors(self):
		return self._messages[ErrorLevel.INT_ERROR]

	@property
	def all_errors(self):
		return self.errors + self.internal_errors

	def disassemble(self, source, output):
		unpacker = msgpack.Unpacker(source, encoding='utf8')

		while True:
			try:
				instruction = Instruction.from_unpacker(unpacker)
			except msgpack.OutOfData:
				break

			output.write("{}\n".format(instruction.pretty_string()))

	def _check_parameter(self, param_type, expected_type):
		if expected_type is None:
			okay = True
		else:
			okay = param_type in expected_type
		return okay

	def _warn(self, inst, warning):
		self._message(ErrorLevel.WARNING, inst, warning)

	def _error(self, inst, error):
		self._message(ErrorLevel.ERROR, inst, error)

	def _int_error(self, inst, error):
		self._message(ErrorLevel.INT_ERROR, inst, error)

	def _message(self, level, inst, message):
		msg = AssemblerMessage(level, inst.line, inst.col, message)
		self._messages[level].append(msg)

	def _emit(self, opcode, *parameters):
		self._result.append(Instruction(opcode, parameters))

	def _write_result(self, output):
		for inst in self._result:
			self._write(output, inst.opcode)
			self._write(output, inst.parameters)

	def _write(self, output, value):
		output.write(msgpack.packb(value, use_bin_type=True))

	TYPE_INFO = {
		# Opcode: (Max#, TokenTypes for Param #1, TokenTypes for Param #2, ...),
		Opcode.NOP: (0,),
		Opcode.PUSH: (None, None),
		Opcode.SEND: (1, (TokenType.START_LIST,)),
		Opcode.SWAP: (1, (TokenType.INTEGER,)),
		Opcode.DUP: (1, (TokenType.INTEGER,)),
		Opcode.APPEND: (1, (TokenType.INTEGER,)),
		Opcode.ADD: (0,),
		Opcode.SUB: (0,),
		Opcode.MUL: (0,),
		Opcode.DIV: (0,),
		Opcode.RECV: (0,),
		Opcode.LISTEN: (1, (TokenType.INTEGER,)),
		Opcode.DICT: (1, (TokenType.INTEGER,)),
		Opcode.LIST: (1, (TokenType.INTEGER,)),
		Opcode.PUT: (1, (TokenType.INTEGER,)),
		Opcode.LOOKUP: (1, (TokenType.INTEGER, TokenType.STRING)),
		Opcode.LEN: (0,),
		Opcode.SENDI: (1, (TokenType.START_LIST,)),
		Opcode.POP: (1, (TokenType.INTEGER,)),
	}

