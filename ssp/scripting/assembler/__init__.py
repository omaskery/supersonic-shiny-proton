

from .parser import Parser, Instruction
from ..opcode import Opcode
from .lexer import Lexer


import msgpack


class Assembler(object):

	def assemble(self, source, output):
		lexer = Lexer(source)
		parser = Parser(lexer)

		while True:
			instruction = parser.parse_instruction()

			if instruction is None:
				break

			# determine whether to use the ARGPUSH rule
			use_argpush = not instruction.inhibit_argpush
			if instruction.opcode == Opcode.PUSH:
				use_argpush = False

			if use_argpush:
				for parameter in instruction.parameters:
					self._write(output, Opcode.PUSH)
					self._write(output, [parameter])
				parameters = []
				if len(instruction.parameters) > 0:
					parameters.append(len(instruction.parameters))
			else:
				parameters = instruction.parameters

			self._write(output, instruction.opcode)
			self._write(output, parameters)

	def disassemble(self, source, output):
		unpacker = msgpack.Unpacker(source, encoding='utf8')

		while True:
			try:
				instruction = Instruction.from_unpacker(unpacker)
			except msgpack.OutOfData:
				break

			output.write("{}\n".format(instruction.pretty_string()))

	def _write(self, output, value):
		output.write(msgpack.packb(value, use_bin_type=True))

