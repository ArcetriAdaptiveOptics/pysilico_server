#!/usr/bin/env python
import sys
from plico.utils.config_file_manager import ConfigFileManager
from pysilico_server.process_monitor.runner import Runner
from pysilico_server.utils.constants import Constants

__version__ = "$Id: tipico_process_monitor.py 26 2018-01-26 19:06:25Z lbusoni $"


def main():
    runner= Runner()
    configFileManager= ConfigFileManager(Constants.APP_NAME,
                                         Constants.APP_AUTHOR,
                                         Constants.THIS_PACKAGE)
    configFileManager.installConfigFileFromPackage()
    argv= ['', configFileManager.getConfigFilePath(),
           Constants.PROCESS_MONITOR_CONFIG_SECTION]
    sys.exit(runner.start(argv))


if __name__ == '__main__':
    main()
