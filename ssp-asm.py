#!/usr/bin/env python3


from ssp.scripting.assembler import Assembler
import argparse


def main():
	args = get_args()
	print(args)


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

