

from .parser import Parser, Instruction, NodeType
from ..opcode import Opcode
from .lexer import Lexer


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
		self._lookup_table = {}
		self._messages = {
			ErrorLevel.WARNING: [],
			ErrorLevel.ERROR: [],
			ErrorLevel.INT_ERROR: [],
		}

	def assemble(self, source, output):
		lexer = Lexer(source)
		parser = Parser(lexer)
		special = {
			'LABEL': self._label_statement,
		}
		offset = 0

		while True:
			instruction = parser.parse_instruction()

			if instruction is None:
				break

			print(instruction.opcode.pretty_str(prefix="opcode: "))
			for index, parameter in enumerate(instruction.parameters):
				print(parameter.pretty_str(indent=1, prefix="param [{}] ".format(index)))

			opcode_str = instruction.opcode.value
			if opcode_str.upper() in special:
				special[opcode_str.upper()](instruction, offset)
				continue

			opcode = Opcode.from_string(opcode_str)
			offset += 1

			if opcode is None:
				self._error(instruction, "unknown opcode: {}".format(
					opcode_str
				))
				continue

			info = Assembler.TYPE_INFO.get(opcode, None)
			if info is None:
				self._int_error(instruction, "no type info for opcode {}".format(
					opcode_str
				))
				continue
			if len(info) < 1:
				self._int_error(instruction, "malformed type info for opcode {}".format(
					opcode_str
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
			for index, param_node in enumerate(instruction.parameters):
				if index < len(param_types):
					expected_types = param_types[index]
				else:
					param_types[-1]
				okay = self._check_parameter(param_node.type, expected_types)
				if not okay:
					self._error(instruction, "param {} of {} is type {}, valid types: {}".format(
						index + 1, opcode_str,
						NodeType.to_string(param_node.type),
						", ".join(map(NodeType.to_string, expected_types))
					))
					bad_types += 1
				parameters.append(param_node) # don't collapse to value yet, do later
			if bad_types > 0:
				continue

			self._emit(opcode, *parameters)

		# if no errors, do output pass
		if len(self.all_errors) == 0:
			self._write_result(output)

		return self.warnings + self.all_errors

	def _label_statement(self, inst, offset):
		if len(inst.parameters) != 1:
			self._error(inst, "label statements take one identifier parameter")
			return
		label_node = inst.parameters[0]
		if label_node.type != NodeType.IDENTIFIER:
			self._error(inst, "label statement argument must be an identifier")
			return
		label = label_node.value
		if label not in self._lookup_table:
			self._lookup_table[label] = offset
		else:
			self._error("redefinition of label '{}'".format(label))

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
		return expected_type is None or param_type in expected_type

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
			try:
				self._write(output, inst.parameters.collapse_to_value(self._lookup_table))
			except KeyError as ke:
				missing_label = ke.args[0]
				self._error(inst, "undefined label '{}'".format(missing_label))

	def _write(self, output, value):
		output.write(msgpack.packb(value, use_bin_type=True))

	TYPE_INFO = {
		# Opcode: (Max#, TokenTypes for Param #1, TokenTypes for Param #2, ...),
		Opcode.NOP: (0,),
		Opcode.PUSH: (None, None),
		Opcode.SEND: (1, (NodeType.LIST_LITERAL,)),
		Opcode.SWAP: (1, (NodeType.INT_LITERAL,)),
		Opcode.DUP: (1, (NodeType.INT_LITERAL,)),
		Opcode.APPEND: (1, (NodeType.INT_LITERAL,)),
		Opcode.ADD: (0,),
		Opcode.SUB: (0,),
		Opcode.MUL: (0,),
		Opcode.DIV: (0,),
		Opcode.RECV: (0,),
		Opcode.LISTEN: (1, (NodeType.INT_LITERAL,)),
		Opcode.DICT: (1, (NodeType.INT_LITERAL,)),
		Opcode.LIST: (1, (NodeType.INT_LITERAL,)),
		Opcode.PUT: (1, (NodeType.INT_LITERAL,)),
		Opcode.LOOKUP: (1, (NodeType.INT_LITERAL, NodeType.STR_LITERAL)),
		Opcode.LEN: (0,),
		Opcode.SENDI: (1, (NodeType.LIST_LITERAL,)),
		Opcode.POP: (1, (NodeType.INT_LITERAL,)),
	}

