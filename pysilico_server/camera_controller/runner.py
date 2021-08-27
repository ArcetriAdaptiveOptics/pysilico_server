import os
import time
from plico.utils.base_runner import BaseRunner
from pysilico_server.devices.simulated_camera import \
    SimulatedPyramidWfsCamera
from pysilico_server.devices.simulated_auxiliary_camera import \
    SimulatedAuxiliaryCamera
from plico.utils.logger import Logger
from plico.utils.control_loop import FaultTolerantControlLoop
from plico.utils.decorator import override
from pysilico_server.camera_controller.camera_controller import \
    CameraController
from plico.rpc.zmq_ports import ZmqPorts
import functools


def ContextWrapper():
    def wrapperFunc(f):
        @functools.wraps(f)
        def wrapper_vimba(self, *args, **kwds):
            from vimba import Vimba
            with Vimba.get_instance():
                with self._vimbacamera:
                    return f(self, *args, **kwds)

        def wrapper_generic(self, *args, **kwds):
            return f(self, *args, **kwds)

        def wrapper(self, *args, **kwds):
            if self._use_vimba_wrapper:
                return wrapper_vimba(self, *args, **kwds)
            else:
                return wrapper_generic(self, *args, **kwds)
        return wrapper

    return wrapperFunc


class Runner(BaseRunner):

    RUNNING_MESSAGE = "Camera controller is running."

    def __init__(self):
        BaseRunner.__init__(self)
        self._use_vimba_wrapper = False

    def _createCameraDevice(self):
        cameraDeviceSection = self.configuration.getValue(
            self.getConfigurationSection(), 'camera')
        cameraModel = self.configuration.deviceModel(cameraDeviceSection)
        if cameraModel == 'simulatedPyramidWfsCamera':
            self._createSimulatedPyramidWfsCamera(cameraDeviceSection)
        elif cameraModel == 'simulatedAuxiliaryCamera':
            self._createSimulatedAuxiliaryCamera(cameraDeviceSection)
        elif cameraModel == 'avt':
            self._createAvtCamera(cameraDeviceSection)
        else:
            raise KeyError('Unsupported camera model %s' % cameraModel)

    def _createSimulatedPyramidWfsCamera(self, cameraDeviceSection):
        cameraName = self.configuration.deviceName(cameraDeviceSection)
        self._camera = SimulatedPyramidWfsCamera(cameraName)
        self._setBinning(cameraDeviceSection)

    def _createSimulatedAuxiliaryCamera(self, cameraDeviceSection):
        cameraName = self.configuration.deviceName(cameraDeviceSection)
        self._camera = SimulatedAuxiliaryCamera(cameraName)
        self._setBinning(cameraDeviceSection)

    def _createAvtCamera(self, cameraDeviceSection):
        from pysilico_server.devices.avtCamera import AvtCamera
        from vimba import Vimba
        ipAddress = self.configuration.getValue(cameraDeviceSection,
                                                'ip_address')
        streamBytesPerSecond = self.configuration.getValue(
            cameraDeviceSection, 'streambytespersecond', getint=True)
        cameraName = self.configuration.deviceName(cameraDeviceSection)
        with Vimba.get_instance() as v:
            self._vimbacamera = v.get_camera_by_id(ipAddress)
        self._camera = AvtCamera(self._vimbacamera, cameraName)
        self._camera.setStreamBytesPerSecond(streamBytesPerSecond)
        self._setBinning(cameraDeviceSection)
        self._use_vimba_wrapper = True

    def _setBinning(self, cameraDeviceSection):
        try:
            binning = self.configuration.getValue(
                cameraDeviceSection, 'binning', getint=True)
            self._camera.setBinning(binning)
        except Exception:
            self._logger.warn(
                "binning not set (not specified in configuration?)")

    def _replyPort(self):
        return self.configuration.replyPort(self.getConfigurationSection())

    def _publisherPort(self):
        return self.configuration.publisherPort(self.getConfigurationSection())

    def _statusPort(self):
        return self.configuration.statusPort(self.getConfigurationSection())

    def _setUp(self):
        self._logger = Logger.of("Camera Controller runner")

        self._zmqPorts = ZmqPorts.fromConfiguration(
            self.configuration, self.getConfigurationSection())
        self._replySocket = self.rpc().replySocket(
            self._zmqPorts.SERVER_REPLY_PORT)
        self._publishSocket = self.rpc().publisherSocket(
            self._zmqPorts.SERVER_PUBLISHER_PORT, hwm=100)
        self._statusSocket = self.rpc().publisherSocket(
            self._zmqPorts.SERVER_STATUS_PORT, hwm=1)
        self._displaySocket = self.rpc().publisherSocket(
            self._zmqPorts.SERVER_DISPLAY_PORT, hwm=1)

        self._createCameraDevice()
        # self._camera.startAcquisition()

        self._controller = CameraController(
            self.name,
            self._zmqPorts,
            self._camera,
            self._replySocket,
            self._publishSocket,
            self._statusSocket,
            self._displaySocket,
            self.rpc())

    @ContextWrapper()
    def _runLoop(self):
        self._logRunning()

        self._camera.startAcquisition()
        FaultTolerantControlLoop(
            self._controller,
            Logger.of("Camera Controller control loop"),
            time,
            0.02).start()
        self._logger.notice("Terminated")

    @override
    def run(self):
        self._setUp()
        self._runLoop()
        return os.EX_OK

    @override
    def terminate(self, signal, frame):
        self._controller.terminate()
