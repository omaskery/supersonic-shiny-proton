

from .lexer import Lexer
from .parser import Parser, Instruction


import msgpack


class Assembler(object):

	def assemble(self, source, output):
		lexer = Lexer(source)
		parser = Parser(lexer)

		while True:
			instruction = parser.parse_instruction()

			if instruction is None:
				break

			self._write(output, instruction.opcode)
			self._write(output, instruction.parameters)

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

