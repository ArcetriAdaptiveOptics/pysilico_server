#!/usr/bin/env python
import logging
from plico.utils.kill_process_by_name import killProcessByName
from pysilico_server.utils.constants import Constants

__version__= "$Id: tipico_stop.py 31 2018-01-27 10:47:29Z lbusoni $"



def main():
    logging.basicConfig(level=logging.INFO)
    processNames= [Constants.START_PROCESS_NAME,
                   Constants.SERVER_PROCESS_NAME,
                   ]

    for each in processNames:
        killProcessByName(each)
