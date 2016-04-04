#!/usr/bin/env python3


from ssp.scripting.assembler import Assembler
from ssp.scripting.source import FileSource
import argparse
import os


def main():
	args = get_args()

	if args.verbose is not None:
		print("verbose level:", args.verbose)
	else:
		args.verbose = 0

	if args.output is None:
		filepath = os.path.basename(args.input.name) + ".bin"
		args.output = open(filepath, 'wb')

	if args.verbose > 0:
		print("input path: ", args.input.name)
		print("output path:", args.output.name)

	source = FileSource(args.input, args.input.name)
	assembler = Assembler()
	assembler.assemble(source, args.output)


def get_args():
	parser = argparse.ArgumentParser(
		description="assembler for the Supersonic Shiny Proton assembly"
	)
	parser.add_argument(
		'input', type=argparse.FileType('r', encoding='utf8'),
		help='the input assembly file to be assembled'
	)
	parser.add_argument(
		'-o', '--output', type=argparse.FileType('wb'),
		help='the output binary file to be generated'
	)
	parser.add_argument(
		'-v', '--verbose', action='count',
		help='enables verbose output'
	)
	return parser.parse_args()


if __name__ == "__main__":
	main()

