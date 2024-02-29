from pathlib import Path
import sys
import logging

from panid.panid import panid

log = logging.getLogger(__name__)

def bin(args = None):
    import argparse

    parser = argparse.ArgumentParser("panid", description="Convert between IDs quickly!")

    parser.add_argument("--input_file", type=Path, help="An input .csv file to convert")
    parser.add_argument("--output", type=Path, help="An output file to save to")
    parser.add_argument("conversion_string", help="A conversion string to use", nargs="+")
    parser.add_argument("--verbose", "-v", action="store_true", help="Increase verbosity")

    args = parser.parse_args(args)

    if args.verbose:
        root_logger = logging.getLogger("panid")
        for h in root_logger.handlers:
            h.setLevel(logging.DEBUG)

    log.debug(f"Starting PanID with args {args}")

    out_stream = args.output.open("w+") if args.output else sys.stdout
    in_stream = args.input_file.open("r") if args.input_file else sys.stdin

    panid(in_stream, out_stream, conversions = args.conversion_string)


