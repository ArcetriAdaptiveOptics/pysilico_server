#!/usr/bin/env python
import sys
from plico.utils.config_file_manager import ConfigFileManager
from pysilico_server.camera_controller.runner import Runner
from pysilico_server.utils.constants import Constants

__version__ = "$Id: tipico_mirror_controller_2.py 31 2018-01-27 10:47:29Z lbusoni $"



def main():
    runner= Runner()
    configFileManager= ConfigFileManager(Constants.APP_NAME,
                                         Constants.APP_AUTHOR,
                                         Constants.THIS_PACKAGE)
    configFileManager.installConfigFileFromPackage()
    argv= ['', configFileManager.getConfigFilePath(),
           Constants.SERVER_2_CONFIG_SECTION]
    sys.exit(runner.start(argv))


if __name__ == '__main__':
    main()
