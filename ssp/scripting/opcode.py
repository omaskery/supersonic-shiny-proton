

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
	SENDI = 17
	POP = 18

	@classmethod
	def from_string(cls, string):
		return {
			'NOP': cls.NOP,
			'PUSH': cls.PUSH,
			'SEND': cls.SEND,
			'SENDI': cls.SENDI,
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
			'POP': cls.POP,
		}[string.upper()]

	@classmethod
	def to_string(cls, integer):
		return {
			cls.NOP: 'NOP',
			cls.PUSH: 'PUSH',
			cls.SEND: 'SEND',
			cls.SENDI: 'SENDI',
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
			cls.POP: 'POP',
		}[integer]

