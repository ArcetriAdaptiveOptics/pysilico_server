
__version__ = "$Id: constants.py 31 2018-01-27 10:47:29Z lbusoni $"


class Constants:
    APP_NAME= "inaf.arcetri.ao.pysilico_server"
    APP_AUTHOR= "INAF Arcetri Adaptive Optics"
    THIS_PACKAGE= 'pysilico_server'

    PROCESS_MONITOR_CONFIG_SECTION= 'processMonitor'
    SERVER_1_CONFIG_SECTION= 'avt1'
    SERVER_2_CONFIG_SECTION= 'avt2'

    # TODO: must be the same of console_scripts in setup.py
    START_PROCESS_NAME= 'pysilico_start'
    STOP_PROCESS_NAME= 'pysilico_stop'
    KILL_ALL_PROCESS_NAME= 'pysilico_kill_all'
    SERVER_1_PROCESS_NAME= 'pysilico_server_1'
    SERVER_2_PROCESS_NAME= 'pysilico_server_2'
