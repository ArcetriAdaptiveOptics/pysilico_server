#!/usr/bin/env python
import sys
from pysilico_server.camera_controller.runner import Runner

__version__ = "$Id: tipico_run_mirror_controller.py 26 2018-01-26 19:06:25Z lbusoni $"



def main():
    runner= Runner()
    sys.exit(runner.start(sys.argv))


if __name__ == '__main__':
    main()
