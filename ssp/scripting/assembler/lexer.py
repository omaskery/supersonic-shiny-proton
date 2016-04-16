

class TokenType:
	UNKNOWN = 0
	IDENTIFIER = 1
	INTEGER = 2
	REAL = 3  # should this be float/double split? :S
	STRING = 4
	START_LIST = 5
	END_LIST = 6
	START_DICT= 7
	END_DICT = 8
	COMMA = 9
	COLON = 10

	@classmethod
	def from_string(cls, string):
		return {
			'UNKNOWN': cls.UNKNOWN,
			'IDENTIFIER': cls.IDENTIFIER,
			'INTEGER': cls.INTEGER,
			'REAL': cls.REAL,
			'STRING': cls.STRING,
			'START_LIST': cls.START_LIST,
			'END_LIST': cls.END_LIST,
			'START_DICT': cls.START_DICT,
			'END_DICT': cls.END_DICT,
			'COMMA': cls.COMMA,
			'COLON': cls.COLON,
		}.get(string.upper(), None)

	@classmethod
	def to_string(cls, integer):
		return {
			cls.UNKNOWN: 'UNKNOWN',
			cls.IDENTIFIER: 'IDENTIFIER',
			cls.INTEGER: 'INTEGER',
			cls.REAL: 'REAL',
			cls.STRING: 'STRING',
			cls.START_LIST: 'START_LIST',
			cls.END_LIST: 'END_LIST',
			cls.START_DICT: 'START_DICT',
			cls.END_DICT: 'END_DICT',
			cls.COMMA: 'COMMA',
			cls.COLON: 'COLON',
		}.get(integer, None)

	@classmethod
	def to_type_name(cls, integer):
		return {
			cls.INTEGER: 'integer',
			cls.REAL: 'real',
			cls.STRING: 'string',
			cls.START_LIST: 'list',
			cls.START_DICT: 'dictionary',
		}.get(integer, None)


class Token(object):
	
	def __init__(self, token_type, value=None):
		self._line = 1
		self._col = 1
		self._type = token_type
		self._value = value
		self._pre_whitespace = ""
		self._post_whitespace = ""

	@property
	def type(self):
		return self._type

	@property
	def value(self):
		return self._value

	@property
	def line(self):
		return self._line

	@property
	def col(self):
		return self._col

	@property
	def pos(self):
		return self.line, self.col

	def at(self, line, col=0):
		self._line = line
		self._col = col
		return self

	def with_whitespace(self, pre, post=""):
		self._pre_whitespace = pre
		self._post_whitespace = post
		return self

	def __str__(self):
		return "Token({}, {}) @ {}:{}".format(
			TokenType.to_string(self._type), self._value, self._line, self._col
		)


class Lexer(object):

	def __init__(self, source):
		self._src = source
		self._line = 1
		self._col = 1

		self._next_token = None

	def is_eof(self):
		return self.peek_token() == None

	def peek_token(self):
		if self._next_token is None:
			self._next_token = self._parse_token()
		return self._next_token

	def get_token(self):
		if self._next_token is None:
			self._next_token = self._parse_token()
		result = self._next_token
		self._next_token = None
		return result
	
	def _parse_token(self):
		pre_whitespace = self._skip_whitespace()

		if self._is_eof():
			return None

		symbols = {
			'[': TokenType.START_LIST,
			']': TokenType.END_LIST,
			'{': TokenType.START_DICT,
			'}': TokenType.END_DICT,
			',': TokenType.COMMA,
			':': TokenType.COLON,
		}

		peeked = self._peek()
		if peeked.isalpha():
			return self._parse_identifier(pre_whitespace)
		elif peeked.isdigit() or peeked == '-':
			return self._parse_numeric(pre_whitespace)
		elif peeked == '"':
			return self._parse_string(pre_whitespace)
		elif peeked in symbols:
			return self._token(self._pos(), symbols[peeked], self._get())\
				.with_whitespace(pre_whitespace)
		else:  # consume unknown stuff so naive consumption still causes exit
			print("lexer stopped at:", self._get())

	def _parse_string(self, pre_whitespace):
		pos = self._pos()

		escapes = {
			't': '\t',
			'f': '\f',
			'r': '\r',
			'n': '\n',
			'a': '\a',
			'"': '"',
		}

		string = ''
		if self._peek() != '"':
			return None
		self._get()

		escaped = False
		while not self._is_eof():
			peeked = self._peek()
			if not escaped and peeked != '"':
				string += self._get()
			elif not escaped and peeked == '\\':
				escaped = True
			elif escaped:
				string += escapes[self._get()]
			else:
				if self._peek() == '"':
					self._get()
				else:
					print('expected " at end of string')
				break
		return self._token(pos, TokenType.STRING, string)\
			.with_whitespace(pre_whitespace)

	def _parse_identifier(self, pre_whitespace):
		pos = self._pos()
		identifier = ''
		while not self._is_eof() and self._peek().isalpha():
			identifier += self._get()
		return self._token(pos, TokenType.IDENTIFIER, identifier)\
			.with_whitespace(pre_whitespace)

	def _parse_numeric(self, pre_whitespace):
		pos = self._pos()

		numeric = ''
		specials = {
			'.':  (float, TokenType.REAL),
			'x':  (lambda x: int(x, 16), TokenType.INTEGER),
			'b':  (lambda x: int(x, 2), TokenType.INTEGER),
			None: (int, TokenType.INTEGER),
		}
		seen_special = None
		is_negative = False

		if self._peek() == '-':
			is_negative = True
			self._get()

		while not self._is_eof():
			peeked = self._peek()
			if peeked.isdigit():
				pass
			elif seen_special is None and peeked in specials.keys():
				seen_special = peeked
			else:
				break
			numeric += self._get()

		converter, token_type = specials[seen_special]
		value = converter(numeric)
		if is_negative:
			value = -value

		return self._token(pos, token_type, value).with_whitespace(pre_whitespace)

	def _pos(self):
		return self._line, self._col

	def _token(self, pos, token_type, value=None):
		return Token(token_type, value).at(*pos)

	def _skip_whitespace(self):
		whitespace = ""
		in_comment = False
		while not self._is_eof():
			peeked = self._peek()
			if peeked.isspace():
				if in_comment and peeked == '\n':
					in_comment = False
			elif not in_comment and peeked == '#':
				in_comment = True
			elif in_comment:
				pass
			else:
				break
			whitespace += self._get()
		return whitespace

	def _is_eof(self):
		return self._src.is_eof()

	def _peek(self):
		return self._src.peek()

	def _get(self):
		got = self._src.get()
		if got == '\n':
			self._line += 1
			self._col = 1
		else:
			self._col += 1
		return got

