import threading
import time
import numpy as np
from plico.utils.hackerable import Hackerable
from plico.utils.snapshotable import Snapshotable
from plico.utils.stepable import Stepable
from plico.utils.serverinfoable import ServerInfoable
from plico.utils.logger import Logger
from plico.utils.decorator import override, logEnterAndExit, synchronized
from plico.utils.timekeeper import TimeKeeper
from pysilico.types.camera_frame import CameraFrame
from pysilico.types.camera_status import CameraStatus
from rebin import rebin


class CameraController(Stepable,
                       Snapshotable,
                       Hackerable,
                       ServerInfoable):

    def __init__(self,
                 servername,
                 ports,
                 camera,
                 replySocket,
                 publisherSocket,
                 statusSocket,
                 displaySocket,
                 rpcHandler,
                 timeMod=time):
        self._camera = camera
        self._replySocket = replySocket
        self._publisherSocket = publisherSocket
        self._statusSocket = statusSocket
        self._displaySocket = displaySocket
        self._rpcHandler = rpcHandler
        self._timeMod = timeMod
        self._logger = Logger.of('CameraController')
        Hackerable.__init__(self, self._logger)
        ServerInfoable.__init__(self, servername,
                                ports,
                                self._logger)
        self._isTerminated = False
        self._stepCounter = 0
        self._frameCounter = 0
        self._lastDisplayTimestamp = 0
        self._displayIntervalInSec = 0.05
        self._timekeep = TimeKeeper()
        self._cameraStatus = None
        self._mutexStatus = threading.RLock()
        self._camera.registerCallback(self._publishFrame)
        self._darkFrame = None
        self._mutexDarkFrame = threading.RLock()
        self._last_time = int(time.time())

    @override
    def step(self):
        self._rpcHandler.handleRequest(self, self._replySocket, multi=True)
        self._publishStatus()
        if self._timekeep.inc():
            self._logger.notice(
                'Stepping at %5.2f Hz. FrameCounter %d' % (
                    self._timekeep.rate, self._camera.getFrameCounter()))
        self._stepCounter += 1
        # Ping the camera every now and then to verify that
        # it is still reachable. In case, it will throw an exception
        # that will trigger the reconnection loop.
        now = int(time.time())
        if self._last_time != now:
            self._last_time = now
            _ = self._camera.exposureTime()

    def getStepCounter(self):
        return self._stepCounter

    def terminate(self):
        self._logger.notice("Got request to terminate")
        try:
            self._camera.stopAcquisition()
            self._camera.deinitialize()
        except Exception as e:
            self._logger.warn("Could not stop camera acquisition: %s" %
                              str(e))
        self._isTerminated = True

    @override
    def isTerminated(self):
        return self._isTerminated

    def getShape(self):
        assert False, 'Should not be used, client uses getStatus instead'

    def getDtype(self):
        assert False, 'Should not be used, client uses getStatus instead'

    @logEnterAndExit('Entering setExposureTime',
                     'Executed setExposureTime')
    def setExposureTime(self, exposureTimeInMilliSeconds):
        self._camera.setExposureTime(exposureTimeInMilliSeconds)
        with self._mutexStatus:
            self._cameraStatus = None

    def _getExposureTime(self):
        return self._getCameraStatus().exposureTimeInMilliSec

    @logEnterAndExit('Entering setBinning',
                     'Executed setBinning')
    def setBinning(self, binning):
        self._camera.setBinning(binning)
        with self._mutexStatus:
            self._cameraStatus = None

    def getBinning(self):
        assert False, 'Should not be used, client uses getStatus instead'

    def getDarkFrame(self):
        with self._mutexDarkFrame:
            return self._darkFrame

    @logEnterAndExit('Entering setDarkFrame',
                     'Executed setDarkFrame')
    def setDarkFrame(self, darkFrame):
        with self._mutexDarkFrame:
            self._darkFrame = darkFrame

    def _getCorrectedFrame(self, frame):
        if self._darkFrame is not None:
            with self._mutexDarkFrame:
                return CameraFrame.fromNumpyArray(
                    frame.toNumpyArray() - self._darkFrame.toNumpyArray(),
                    frame.counter())
        else:
            return frame

    def getSnapshot(self, prefix):
        assert False, 'Should not be used, client uses getStatus instead'

    def _publishFrame(self, frame):
        correctedFrame = self._getCorrectedFrame(frame)
        self._rpcHandler.sendCameraFrame(self._publisherSocket, correctedFrame)
        self._logger.debug('frame %d published' % correctedFrame.counter())
        self._publishForDisplay(correctedFrame)

    def _downsizeForDisplay(self, frame):
        DISPLAY_FRAME_SIZE = 256.
        minSize = np.min(frame.toNumpyArray().shape)
        downsizeBy = int(np.ceil(
            minSize / DISPLAY_FRAME_SIZE))
        if downsizeBy > 1:
            array = self._downsizeBySampling(frame.toNumpyArray(),
                                             downsizeBy)
        else:
            array = frame.toNumpyArray()
        return CameraFrame.fromNumpyArray(np.float32(array),
                                          frame.counter())

    def _downsizeByRebin(self, frame, factor):
        return rebin(frame, factor) * factor**2

    def _downsizeBySampling(self, frame, factor):
        return frame[::factor, ::factor]

    def _publishForDisplay(self, frame):
        now = self._timeMod.time()
        if now - self._lastDisplayTimestamp < self._displayIntervalInSec:
            return
        downsizedFrame = self._downsizeForDisplay(frame)
        self._rpcHandler.sendCameraFrame(self._displaySocket,
                                         downsizedFrame)
        self._lastDisplayTimestamp = now

    @synchronized("_mutexStatus")
    def _getCameraStatus(self):
        if self._cameraStatus is None:
            self._logger.debug('get CameraStatus')
            self._cameraStatus = CameraStatus(
                self._camera.name(),
                self._camera.cols(),
                self._camera.rows(),
                self._camera.dtype(),
                self._camera.getBinning(),
                self._camera.exposureTime(),
                self._camera.getFrameRate(),
                self._camera.getParameters())
        return self._cameraStatus

    def _publishStatus(self):
        self._rpcHandler.publishPickable(self._statusSocket,
                                         self._getCameraStatus())

    @logEnterAndExit('Entering setFrameRate',
                     'Executed setFrameRate')
    def setFrameRate(self, frameRate):
        self._camera.setFrameRate(frameRate)
        with self._mutexStatus:
            self._cameraStatus = None

    @logEnterAndExit('Entering setParameter',
                     'Executed setParameter')
    def setParameter(self, name, value):
        self._camera.setParameter(name, value)
        with self._mutexStatus:
            self._cameraStatus = None

