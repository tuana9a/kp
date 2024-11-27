import argparse
import sys

from kp.cmd import RootCmd


def main():
    parser = argparse.ArgumentParser()
    RootCmd(parser)
    args = parser.parse_args(sys.argv[1:])
    args.func(args)


if __name__ == "__main__":
    main()
