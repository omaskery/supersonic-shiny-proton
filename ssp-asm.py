#!/usr/bin/env python3


from ssp.scripting.assembler import Assembler
from ssp.scripting.source import FileSource
import argparse
import sys
import os


def main():
	args = get_args()

	if args.verbose is not None:
		print("verbose level:", args.verbose)
	else:
		args.verbose = 0

	if args.output is None:
		if not args.disasm:
			extension = ".bin"
		else:
			extension = ".asm"

		filepath = os.path.basename(args.input) + extension
		
	if not args.disasm:
		input_file = open(args.input, 'r', encoding='utf8')
		output_file = open(filepath, 'wb')
	else:
		input_file = open(args.input, 'rb')
		output_file = open(filepath, 'w', encoding='utf8')

	if args.verbose > 0:
		print("input path: ", args.input)
		print("output path:", args.output)

	source = FileSource(input_file, args.input)
	assembler = Assembler()
	if not args.disasm:
		messages = assembler.assemble(source, output_file)
	else:
		messages = assembler.disassemble(input_file, output_file)

	exit_code = 0

	if messages is not None and len(messages) > 0:
		warnings, errors, internal_errors = assembler.get_message_counts()
		if not args.disasm and (errors + internal_errors) > 0:
			print("no output generated due to errors")
			exit_code = -1
		for msg in messages:
			print(msg)
		print("  {} warnings, {} errors, {} internal errors".format(
			warnings, errors, internal_errors
		))

	sys.exit(exit_code)

def get_args():
	parser = argparse.ArgumentParser(
		description="assembler for the Supersonic Shiny Proton assembly"
	)
	parser.add_argument(
		'input', help='the input file to be [dis]assembled'
	)
	parser.add_argument(
		'-o', '--output', help='the output file to be generated'
	)
	parser.add_argument(
		'-d', '--disasm', action='store_true',
		help='disassembles a binary file into assembly instead of assembling'
	)
	parser.add_argument(
		'-v', '--verbose', action='count',
		help='enables verbose output'
	)
	return parser.parse_args()


if __name__ == "__main__":
	main()

