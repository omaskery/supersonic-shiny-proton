

from ..instruction import Instruction
from .lexer import TokenType
from ..opcode import Opcode


class NodeType:
	IDENTIFIER = 0
	INT_LITERAL = 1
	REAL_LITERAL = 2
	STR_LITERAL = 3
	LIST_LITERAL = 4
	DICT_LITERAL = 5

	@classmethod
	def to_string(cls, integer):
		return {
			cls.IDENTIFIER: "IDENTIFIER",
			cls.INT_LITERAL: "INT_LITERAL",
			cls.REAL_LITERAL: "REAL_LITERAL",
			cls.STR_LITERAL: "STR_LITERAL",
			cls.LIST_LITERAL: "LIST_LITERAL",
			cls.DICT_LITERAL: "DICT_LITERAL",
		}.get(integer, None)


class Node(object):
	
	def __init__(self, node_type, value):
		self._type = node_type
		self._value = value
		self._line = 1
		self._col = 1

	@property
	def type(self): return self._type
	@property
	def value(self): return self._value
	@property
	def line(self): return self._line
	@property
	def col(self): return self._col

	def at(self, line, col):
		self._line, self._col = line, col
		return self

	def collapse_to_value(self, lookup_table={}):
		simple_nodes = (
			NodeType.INT_LITERAL,
			NodeType.REAL_LITERAL,
			NodeType.STR_LITERAL,
		)
		if self.type in simple_nodes:
			return self.value
		elif self.type == NodeType.LIST_LITERAL:
			return [
				x.collapse_to_value()
				for x in self.value
			]
		elif self.type == NodeType.DICT_LITERAL:
			return dict([
				(key.collapse_to_value(), value.collapse_to_value())
				for key, value in self.value.items()
			])
		elif self.type == NodeType.IDENTIFIER:
			return lookup_table[self.value]

	def pretty_str(self, indent=0, tabsize=2, separator='\n', prefix=""):
		type_name = NodeType.to_string(self.type)

		if self.type in (NodeType.IDENTIFIER, NodeType.INT_LITERAL, NodeType.REAL_LITERAL):
			value_text = str(self.value)
		elif self.type == NodeType.STR_LITERAL:
			value_text = '"{}"'.format(self.value)
		else:
			value_text = None

		text = " " * (indent * tabsize)
		text += prefix
		text += type_name.replace("_", " ").title()
		if value_text is not None:
			text += " ({})".format(value_text)

		if self.type == NodeType.LIST_LITERAL:
			for index, child in enumerate(self.value):
				prefix = "[{}] ".format(index)
				text += separator + child.pretty_str(indent+1, tabsize, separator, prefix)
		elif self.type == NodeType.DICT_LITERAL:
			for key, value in self.value.items():
				text += separator + key.pretty_str(
					indent+1, tabsize, separator, "key: "
				)
				text += separator + value.pretty_str(
					indent+1, tabsize, separator, "value: "
				)

		return text

	def __str__(self):
		return self.pretty_str()


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

		opcode = Node(NodeType.IDENTIFIER, operation.value)
		parameters = []
		while not self._lexer.is_eof() and\
				self._lexer.peek_token().line == operation.line:
			parameter_token = self._lexer.get_token()
			parameters.append(self._parse_value(parameter_token))

		return Instruction(opcode, parameters).at(operation.line, operation.col)

	def _parse_value(self, token):
		mapping = [
			((TokenType.IDENTIFIER,),
				lambda token: Node(NodeType.IDENTIFIER, token.value)),
			((TokenType.INTEGER, TokenType.REAL, TokenType.STRING,),
				lambda token: self._parse_simple_literal(token)),
			((TokenType.START_LIST,),
				lambda token: self._parse_list()),
			((TokenType.START_DICT,),
				lambda token: self._parse_dict()),
		]

		result = None
		for types, handler in mapping:
			if token.type in types:
				if handler is None:
					print("don't know what to do with {} types yet".format(
						TokenType.to_string(token.type)
					))
				else:
					result = handler(token)
				break
		return result

	def _parse_simple_literal(self, token):
		node_type = {
			TokenType.INTEGER: NodeType.INT_LITERAL,
			TokenType.REAL: NodeType.REAL_LITERAL,
			TokenType.STRING: NodeType.STR_LITERAL,
		}[token.type]
		return Node(node_type, token.value)
	
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
		return Node(NodeType.LIST_LITERAL, values)

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
		return Node(NodeType.DICT_LITERAL, values)

