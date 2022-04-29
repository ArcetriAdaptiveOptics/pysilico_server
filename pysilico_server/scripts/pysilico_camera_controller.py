#!/usr/bin/env python
import sys
from pysilico_server.camera_controller.runner import Runner

__version__ = "$Id: tipico_mirror_controller_1.py 31 2018-01-27 10:47:29Z lbusoni $"


def main():
    runner= Runner()
    sys.exit(runner.start(sys.argv))


if __name__ == '__main__':
    main()
