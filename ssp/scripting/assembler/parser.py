

from ..instruction import Instruction
from .lexer import TokenType
from ..opcode import Opcode


class Parser(object):

	def __init__(self, lexer):
		self._lexer = lexer

	def parse_instruction(self):
		operation = self._lexer.get_token()

		if operation is None:
			return None
		if operation.type != TokenType.IDENTIFIER:
			print("expected identifier at", operation.pos)
			return None

		parameters = []
		while not self._lexer.is_eof() and\
				self._lexer.peek_token().line == operation.line:
			parameter_token = self._lexer.get_token()
			parameters.append(self._parse_value(parameter_token))

		opcode = Opcode.from_string(operation.value)

		return Instruction(opcode, parameters).at(operation.line, operation.col)

	def _parse_value(self, token):
		result = [token.type, None]
		mapping = [
			((TokenType.IDENTIFIER,), None),
			((TokenType.INTEGER, TokenType.REAL, TokenType.STRING,),
				lambda token: token.value),
			((TokenType.START_LIST,), lambda token: self._parse_list()),
			((TokenType.START_DICT,), lambda token: self._parse_dict()),
		]
		for types, handler in mapping:
			if token.type in types:
				if handler is None:
					print("don't know what to do with {} types yet".format(
						TokenType.to_string(token.type)
					))
				else:
					result[1] = handler(token)
				break
		return tuple(result)
	
	def _parse_list(self):
		values = []
		first = True
		while self._lexer.peek_token() and self._lexer.peek_token().type != TokenType.END_LIST:
			if not first:
				comma = self._lexer.get_token()
				if comma.type != TokenType.COMMA:
					print("expected comma at", comma.pos)
					break
			value = self._parse_value(self._lexer.get_token())
			values.append(value)
			first = False
		end_token = self._lexer.get_token()
		if end_token.type != TokenType.END_LIST:
			print("expected end of list at", end_token.pos)
		return values

	def _parse_dict(self):
		values = {}
		first = True
		while self._lexer.peek_token().type != TokenType.END_DICT:
			if not first:
				comma = self._lexer.get_token()
				if comma.type != TokenType.COMMA:
					print("expected comma at", comma.pos)
					break
			key_token = self._lexer.get_token()
			if key_token.type != TokenType.STRING:
				print("expected key token at", key_token.pos)
				break
			colon = self._lexer.get_token()
			if colon.type != TokenType.COLON:
				print("expected colon at", colon.pos)
				break
			value = self._parse_value(self._lexer.get_token())
			values[key_token.value] = value
			first = False
		end_token = self._lexer.get_token()
		if end_token.type != TokenType.END_DICT:
			print("expected end of dictionary at", end_token.pos)
		return values

