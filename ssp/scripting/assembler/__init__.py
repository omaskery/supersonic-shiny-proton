

from .lexer import Lexer
from .parser import Parser


class Assembler(object):

	def assemble(self, source, output):
		lexer = Lexer(source)
		parser = Parser(lexer)
		while True:
			instruction = parser.parse_instruction()
			if instruction is None:
				break
			print(instruction)

