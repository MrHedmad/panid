from pathlib import Path
import sys
import logging

log = logging.getLogger(__name__)

def bin(args = None):
    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument("input_file", type=Path, help="An input .csv file to convert")
    parser.add_argument("--output", type=Path, help="An output file to save to")
    parser.add_argument("conversion_string", help="A conversion string to use", nargs="*")

    args = parser.parse_args(args)

    log.debug(f"Starting PanID with args {args}")

    out_stream = args.output.open("w+") if args.output else sys.stdout
    in_stream = args.input.open("r")


