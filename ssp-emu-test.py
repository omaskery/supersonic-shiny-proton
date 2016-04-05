#!/usr/bin/env python3


from ssp.scripting.emulator import Emulator, load_program, BlockingReason
import argparse


def main():
	args = get_args()

	program = load_program(args.input)
	print("loaded {} instructions".format(len(program)))

	emu = Emulator()
	emu.hook_error(
		lambda emu, err: print("error:", err)
	)
	emu.hook_halted(
		lambda emu: print("halted")
	)
	emu.hook_send(
		lambda emu, values: print("sending:", values)
	)
	emu.hook_block(
		lambda emu, reason: print("blocked on", BlockingReason.to_string(reason))
	)

	emu.set_program(program)

	emu.resume()
	while emu.running:
		emu.single_step()
		if emu.running:
			input("...")


def get_args():
	parser = argparse.ArgumentParser(
		description='utility for testing the ssp emulator'
	)
	parser.add_argument(
		'input', type=argparse.FileType('rb'),
		help='the binary to load into the emulator'
	)
	return parser.parse_args()


if __name__ == "__main__":
	main()

