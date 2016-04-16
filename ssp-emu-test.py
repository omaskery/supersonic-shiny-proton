#!/usr/bin/env python3


from ssp.scripting.emulator import Emulator, load_program, BlockingReason
import argparse


class EmuTest(object):

	def __init__(self, program, debug=False, verbose=0):
		self._emu = Emulator(verbose=verbose)
		self._emu.hook_error(self._on_error)
		self._emu.hook_halted(self._on_halted)
		self._emu.hook_send(self._on_send)
		self._emu.hook_block(self._on_block)
		self._emu.set_program(program)

		self._debug = debug
		self._verbose = verbose

		self._services = {
			'sys': self._svc_sys,
			'fs': self._svc_fs,
			'.': self._svc_invoker,
		}

	def test(self):
		self._emu.resume()
		while self._emu.running:
			self._emu.single_step()
			if self._emu.running and self._debug:
				input("...")

	def _on_error(self, emu, err, addr):
		print("error[0x{:04X}]: {}".format(addr, err))

	def _on_halted(self, emu):
		print("halted")

	def _on_send(self, emu, target, values):
		print("sending:", values, "to", target)
		response = None
		service = self._services.get(target, None)
		if service is None:
			emu.trigger_error("unknown target '{}'", target)
			return
		response = service(values)
		if response is not None:
			print("responding to emu:", response)
			emu.receive(target, response)

	def _on_block(self, emu, reason):
		print("blocked on", BlockingReason.to_string(reason))

	def _svc_sys(self, values):
		if len(values) > 0 and values[0] == 'ls':
			return [
				"blah.txt",
				"your_mom"
			]
		else:
			self._emu.trigger_error("unknown syscall '{}'".format(values))

	def _svc_fs(self, values):
		if len(values) > 0 and values[0] == 'open':
			return 0
		elif len(values) > 2 and values[0] == 'write':
			file_handle = values[1]
			data = values[2]
			print("writing '{}' to file handle {}".format(
				data, file_handle
			))
			return 0
		else:
			self._emu.trigger_error("unknown fs operation '{}'".format(
				values
			))

	def _svc_invoker(self, values):
		print("to invoker:", " ".join(map(str, values)))


def main():
	args = get_args()

	program = load_program(args.input)
	print("loaded {} instructions".format(len(program)))

	test = EmuTest(program, debug=args.debug, verbose=args.verbose)
	test.test()


def get_args():
	parser = argparse.ArgumentParser(
		description='utility for testing the ssp emulator'
	)
	parser.add_argument(
		'input', type=argparse.FileType('rb'),
		help='the binary to load into the emulator'
	)
	parser.add_argument(
		'-d', '--debug', action='store_true',
		help='whether to run emulator in debug mode with waits after each step'
	)
	parser.add_argument(
		'-v', '--verbose', action='count',
		help='whether to run emulator in verbose mode'
	)
	return parser.parse_args()


if __name__ == "__main__":
	main()

