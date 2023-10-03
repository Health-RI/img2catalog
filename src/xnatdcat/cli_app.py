import argparse
import xnat
from .xnat_parser import XNAT_to_DCAT
from pathlib import PurePath
from .__about__ import __version__


def __parse_cli_args():
    """Simple argument parser for commandline args"""

    parser = argparse.ArgumentParser(prog="xnatdcat", description="This tool generates DCAT from XNAT")
    parser.add_argument(
        "server",
        type=str,
        help="URI of the server to connect to (including http:// or https://)",
    )
    parser.add_argument(
        "-u",
        "--username",
        default=None,
        type=str,
        help="Username to use, leave empty to use netrc entry or anonymous login.",
    )
    parser.add_argument(
        "-p",
        "--password",
        default=None,
        type=str,
        help=(
            "Password to use with the username, leave empty when using netrc. If a"
            " username is given and no password, there will be a prompt on the console"
            " requesting the password."
        ),
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        type=PurePath,
        help="Destination file to write output to. If not set, the script will print serialized output to stdout.",
    )
    parser.add_argument(
        "-f",
        "--format",
        default="turtle",
        type=str,
        help=(
            "The format that the output should be written in. This value references a"
            " Serializer plugin in RDFlib. Supportd values are: "
            " \"xml\", \"n3\", \"turtle\", \"nt\", \"pretty-xml\", \"trix\", \"trig\", \"nquads\","
            " \"json-ld\" and \"hext\". Defaults to \"turtle\"."
        ),
    )
    parser.add_argument("-V", "--version", action="version", version=f"%(prog)s {__version__}")

    args = parser.parse_args()

    return args


def __connect_xnat(args):
    """Very simple function to connect to XNat and get a session"""
    session = xnat.connect(server=args.server, user=args.username, password=args.password)

    return session


def cli_main():
    args = __parse_cli_args()

    session = __connect_xnat(args)
    g = XNAT_to_DCAT(session)

    if args.output:
        g.serialize(destination=args.output, format=args.format)
    else:
        print(g.serialize(format=args.format))


if __name__ == "__main__":
    cli_main()
