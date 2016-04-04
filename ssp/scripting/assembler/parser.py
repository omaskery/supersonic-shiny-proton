

from .lexer import TokenType


class Opcode:
	NOP = 0
	PUSH = 1
	SEND = 2
	SWAP = 3
	DUP = 4
	APPEND = 5
	ADD = 6
	SUB = 7
	MUL = 8
	DIV = 9
	RECV = 10
	LISTEN = 11
	DICT = 12
	LIST = 13
	PUT = 14
	LOOKUP = 15
	LEN = 16

	@classmethod
	def from_string(cls, string):
		return {
			'NOP': cls.NOP,
			'PUSH': cls.PUSH,
			'SEND': cls.SEND,
			'SWAP': cls.SWAP,
			'DUP': cls.DUP,
			'APPEND': cls.APPEND,
			'ADD': cls.ADD,
			'SUB': cls.SUB,
			'MUL': cls.MUL,
			'DIV': cls.DIV,
			'RECV': cls.RECV,
			'LISTEN': cls.LISTEN,
			'DICT': cls.DICT,
			'LIST': cls.LIST,
			'PUT': cls.PUT,
			'LOOKUP': cls.LOOKUP,
			'LEN': cls.LEN,
		}[string.upper()]

	@classmethod
	def to_string(cls, integer):
		return {
			cls.NOP: 'NOP',
			cls.PUSH: 'PUSH',
			cls.SEND: 'SEND',
			cls.SWAP: 'SWAP',
			cls.DUP: 'DUP',
			cls.APPEND: 'APPEND',
			cls.ADD: 'ADD',
			cls.SUB: 'SUB',
			cls.MUL: 'MUL',
			cls.DIV: 'DIV',
			cls.RECV: 'RECV',
			cls.LISTEN: 'LISTEN',
			cls.DICT: 'DICT',
			cls.LIST: 'LIST',
			cls.PUT: 'PUT',
			cls.LOOKUP: 'LOOKUP',
			cls.LEN: 'LEN',
		}[integer]


class Instruction(object):

	def __init__(self, opcode, parameters):
		self._opcode = opcode
		self._parameters = parameters

		self._line = 1
		self._col = 1

	def at(self, line, col):
		self._line = line
		self._col = col
		return self

	def __str__(self):
		return "{} ({}): {}".format(
			Opcode.to_string(self._opcode), self._opcode,
			", ".join(map(str, self._parameters))
		)


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

		return Instruction(opcode, parameters)

	def _parse_value(self, token):
		if token.type == TokenType.IDENTIFIER:
			print("don't know what to do with identifiers here yet", token.pos)
		elif token.type in (TokenType.INTEGER, TokenType.REAL, TokenType.STRING):
			return token.value
		elif token.type == TokenType.START_LIST:
			return self._parse_list()
		elif token.type == TokenType.START_DICT:
			return self._parse_dict()
		else:
			print("unexpected token", token)
	
	def _parse_list(self):
		values = []
		first = True
		while self._lexer.peek_token().type != TokenType.END_LIST:
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

