import os

__version__= "$Id: process_startup_helper.py 26 2018-01-26 19:06:25Z lbusoni $"


class ProcessStartUpHelper(object):

    def __init__(self):
        self._moduleRoot= 'pysilico_server'


    def cameraControllerStartUpScriptPath(self):
        return os.path.join(self._moduleRoot,
                            'camera_controller',
                            'pysilico_run_camera_controller.py')


    def killAllProcessesStartUpScriptPath(self):
        return os.path.join(self._moduleRoot,
                            'utils',
                            'pysilico_kill_processes.py')


    def processProcessMonitorStartUpScriptPath(self):
        return os.path.join(self._moduleRoot,
                            'process_monitor',
                            'pysilico_run_process_monitor.py')


    def processProcessMonitorStopScriptPath(self):
        return os.path.join(self._moduleRoot,
                            'utils',
                            'pysilico_server_stop.py')
