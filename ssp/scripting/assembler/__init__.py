

from .lexer import Lexer


class Assembler(object):

	def assemble(self, source, output):
		lexer = Lexer(source)
		while lexer.peek_token() is not None:
			token = lexer.get_token()
			print(token)

