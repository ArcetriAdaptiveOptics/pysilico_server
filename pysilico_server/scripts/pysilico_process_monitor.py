#!/usr/bin/env python
import sys
from plico.utils.config_file_manager import ConfigFileManager
from plico.utils.process_monitor_runner import ProcessMonitorRunner
from pysilico_server.utils.constants import Constants


def main():
    prefix = Constants.DEFAULT_SERVER_CONFIG_SECTION_PREFIX
    runner = ProcessMonitorRunner(Constants.SERVER_PROCESS_NAME,
                                  default_server_config_prefix=prefix)
    configFileManager = ConfigFileManager(Constants.APP_NAME,
                                          Constants.APP_AUTHOR,
                                          Constants.THIS_PACKAGE)
    configFileManager.installConfigFileFromPackage()
    argv = ['', configFileManager.getConfigFilePath(),
            Constants.PROCESS_MONITOR_CONFIG_SECTION]
    sys.exit(runner.start(argv))


if __name__ == '__main__':
    main()

