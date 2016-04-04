

class Source(object):

	@property
	def name(self):
		raise Exception("unimplemented")

	def is_eof(self):
		raise Exception("unimplemented")

	def peek(self):
		raise Exception("unimplemented")

	def get(self):
		raise Exception("unimplemented")


class FileSource(Source):

	BUFFER_SIZE = 2048

	def __init__(self, handle, name):
		self._handle = handle
		self._name = name
		self._buf = ''

	@property
	def name(self):
		return self._name

	def is_eof(self):
		self._fill_buffer()
		return len(self._buf) <= 0

	def peek(self):
		self._fill_buffer()
		if len(self._buf) > 0:
			return self._buf[0]
		else:
			return None

	def get(self):
		self._fill_buffer()
		if len(self._buf) > 0:
			result = self._buf[0]
			self._buf = self._buf[1:]
		else:
			result = None
		return result

	def _fill_buffer(self):
		remaining = FileSource.BUFFER_SIZE - len(self._buf)
		if remaining > 0:
			read = self._handle.read(remaining)
			self._buf = self._buf + read

