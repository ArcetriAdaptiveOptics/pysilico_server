import numpy as np
import time
from plico.utils.decorator import override, returns
from pysilico_server.devices.abstract_camera import AbstractCamera
from plico.utils.logger import Logger
from plico.utils.concurrent_loop import ConcurrentLoop
from plico.utils.convergeable import Convergeable
from pysilico.types.camera_frame import CameraFrame


__version__= "$Id: $"



class SimulatedFrameProducer(Convergeable):

    def __init__(self, simulatedCamera):
        self._camera= simulatedCamera

        self._cycleCounter= 0
        self._logger= Logger.of("SimulatedFrameProducer")


    @override
    @returns(bool)
    def hasConverged(self):
        return False


    @override
    def performOneConvergenceStep(self):
        self._camera.produceFrame()
        self._cycleCounter += 1


    @override
    def measureConvergence(self):
        pass




class BaseSimulatedCamera(AbstractCamera):
    SENSOR_H= 1024
    SENSOR_W= 1360
    DTYPE= np.uint16
    MAX_VALUE= 4096


    def __init__(self, name='Simulated Camera'):
        self._name= name
        self._logger= Logger.of('SimulatedCamera')
        self._counter= 0
        self._delay= 0.00
        self._exposureTimeMs= 10.0
        self._frameRate= 1000./ self._exposureTimeMs
        self._binning= 1
        self._totalFluxPerMilliSecond= 2e6
        self._noiseInCount= 10.

        self._lastValidFrame= None
        self._callbackList= []
        self._buildFrameProducerLoop()

        self._logger.notice('Simulated camera initialized')
        self._logger.notice('Sensor size (H,W) %s %s' % (
            self.SENSOR_H, self.SENSOR_W))
        self._raiseExceptionOnDeinitialize= False


    def raiseExceptionOnDeinitialize(self, trueOrFalse):
        self._raiseExceptionOnDeinitialize= trueOrFalse


    def _buildFrameProducerLoop(self):
        self._frameProducer= SimulatedFrameProducer(self)
        self._frameProducerLoop= ConcurrentLoop(
            "SimulatedFrameProducerLoop", self._frameProducer, 0.01,
            self._logger.error)
        self._frameProducerLoop.initialize()


    def _notifyListenersAboutNewFrame(self):
        for callback in self._callbackList:
            callback(self._lastValidFrame)


    def produceFrame(self):
        frame= self._computeFrameFromWavefront()
        self._lastValidFrame= CameraFrame(frame, self._counter)
        self._notifyListenersAboutNewFrame()
        self._counter+= 1


    @override
    def deinitialize(self):
        if self._raiseExceptionOnDeinitialize:
            raise Exception('Asked to fail on deinitialize')
        else:
            self._frameProducerLoop.deinitialize()


    @override
    def startAcquisition(self):
        self._frameProducerLoop.close()


    @override
    def stopAcquisition(self):
        self._frameProducerLoop.open()


    @override
    def registerCallback(self, callback):
        self._callbackList.append(callback)


    def frameCounter(self):
        return self._counter


    @override
    def name(self):
        return self._name


    @override
    def rows(self):
        return int(float(self.SENSOR_H)/ self._binning)


    @override
    def cols(self):
        return int(float(self.SENSOR_W)/ self._binning)


    @override
    def dtype(self):
        return self.DTYPE


    @override
    @returns(np.ndarray)
    def readFrame(self, timeoutMilliSec=2000):
        return self._computeFrameFromWavefront()


    def setNoiseInCount(self, noise):
        self._noiseInCount= noise


    def setTotalFluxPerMilliSecond(self, totalFluxPerMilliSec):
        self._totalFluxPerMilliSecond= totalFluxPerMilliSec


    def _computeFrameFromWavefront(self):
        pixels = np.zeros((self.rows(), self.cols()),
                          dtype=np.float)

        self._counter += 1
        time.sleep(1./ self.getFrameRate())
        return pixels.astype(self.DTYPE)


    @override
    def setExposureTime(self, exposureTimeInMilliSeconds):
        self._exposureTimeMs= exposureTimeInMilliSeconds


    @override
    def exposureTime(self):
        return self._exposureTimeMs


    @override
    def setBinning(self, binning):
        self._logger.notice("setting binning to %d" % binning)
        self._binning= binning


    @override
    def getBinning(self):
        return self._binning


    @override
    def getFrameRate(self):
        return self._frameRate


    @override
    def setFrameRate(self, frameRate):
        self._frameRate= frameRate


    @override
    def getFrameCounter(self):
        return self._counter
