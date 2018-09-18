#!/usr/bin/env python

import time
import numpy as np
import textwrap
import threading
from plico.utils.decorator import cacheResult, logEnterAndExit, \
    synchronized, override
from pysilico_server.devices.abstract_camera import AbstractCamera
from plico.utils.logger import Logger
from pysilico.types.camera_frame import CameraFrame

__version__ = "$Id: avtCamera.py 268 2017-04-12 21:54:14Z lbusoni $"


def _importVimbaInALazyWay():
    from pymba import vimba
    return vimba


class Vimba(object):

    NOT_AVAILABLE= 'Not Available'
    BINNING_HORIZONTAL= 'BinningHorizontal'
    BINNING_VERTICAL= 'BinningVertical'
    DECIMATION_HORIZONTAL= 'DecimationHorizontal'
    DECIMATION_VERTICAL= 'DecimationVertical'
    FRAME_STATUS_COMPLETE= 0

    def __init__(self):
        self._vimbaModule= _importVimbaInALazyWay()
        self._vimba = self._vimbaModule.Vimba()
        self._initialized= False


    def startUp(self):
        if not self._initialized:
            self._vimba.startup()
            self._initialized= True


    def tearDown(self):
        self._vimba.shutdown()


    @cacheResult
    def getCamera(self, ipaddress):
        return self._vimbaModule.VimbaCamera(ipaddress)


    def getSystemFeatures(self):
        system = self._vimba.getSystem()
        res={}
        for featureName in system.getFeatureNames():
            try:
                featureValue= system.__getattr__(featureName)
            except Exception:
                featureValue= self.NOT_AVAILABLE
            res[featureName]= featureValue
        return res

    def getVersion(self):
        return self._vimba.getVersion()


class AvtCamera(AbstractCamera):
    def __init__(self, vimbacamera, name):
        self._name = name
        self._camera= vimbacamera
        self._logger= Logger.of('AvtCamera')
        self._binning= 1
        self._counter = 0
        self._isContinuouslyAcquiring= False
        self._callbackList= []
        self._mutex= threading.RLock()
        self._lastValidFrame= CameraFrame(np.zeros((4, 4)), counter=0)
        self._initialize()


    def _initialize(self):
        try:
            self._camera.openCamera()
        except Exception:
            raise Exception(
                "Cannot open camera. Maybe another process is using it?")

        # Limit data rate from camera
#         try:
#             streamBytesPerSecond = conf().getint('camera', 'streamBytesPerSecond')
#         except:
#             streamBytesPerSecond = 100000000
        streamBytesPerSecond = 10000000
        self.setStreamBytesPerSecond(streamBytesPerSecond)

        self._resetBinningAndOffset()

        if self.pixelFormat() == 'Mono12':
            self.BYTES_PER_PIXEL= 2
            self._dtype= np.uint16
        else:
            raise Exception('Format %s is not supported' % self.pixelFormat())

        self._logCameraInfo()
        self._logger.notice('AVT camera initialized')



    @logEnterAndExit('Entering _createFrames',
                     'Executed _createFrames',
                     'debug')
    @synchronized("_mutex")
    def _createFrames(self):
        # create new frames for the camera
        self._frame = self._camera.getFrame()    # creates a frame
        self._frame.announceFrame()


    def _isBinningAvailable(self):
        feat= list(self.getCameraFeatures().keys())
        return Vimba.BINNING_HORIZONTAL in feat and \
            Vimba.BINNING_VERTICAL in feat


    def _isDecimationAvailable(self):
        feat= list(self.getCameraFeatures().keys())
        return Vimba.DECIMATION_HORIZONTAL in feat and \
            Vimba.DECIMATION_VERTICAL in feat


    @synchronized("_mutex")
    def _resetBinningAndOffset(self):

        restartAcquistion= False
        if self._isContinuouslyAcquiring:
            self.stopAcquisition()
            restartAcquistion= True

        if self._isBinningAvailable():
            self._camera.BinningHorizontal= self._binning
            self._camera.BinningVertical= self._binning
        elif self._isDecimationAvailable():
            self._camera.DecimationHorizontal= self._binning
            self._camera.DecimationVertical= self._binning
        else:
            raise Exception("Neither binning nor decimation available")

        self._camera.OffsetX=0
        self._camera.OffsetY=0
        self._camera.Height= self._camera.SensorHeight // self._binning
        self._camera.Width= self._camera.SensorWidth // self._binning
        self._camera.PixelFormat= 'Mono12'
        self._camera.GVSPPacketSize=1500
        self._timeStampTickFrequency= self._camera.GevTimestampTickFrequency
        self._logger.notice(
            'Binning set to %d. Frame shape (w,h): (%d, %d) '
            'Left bottom pixel (%d, %d)'
            % (self._binning, self._camera.Width, self._camera.Height,
               self._camera.OffsetX, self._camera.OffsetY))

        if restartAcquistion:
            self.startAcquisition()


    @synchronized("_mutex")
    def _logCameraInfo(self):
        self._logger.notice('Camera: %s at %s - ID: %s' % (
                            self.deviceModelName(),
                            self.ipAddress(),
                            self.deviceID()))
        self._logger.notice('Sensor is %d rows x %d cols, %d bits/pixel' % (
            self._camera.SensorHeight,
            self._camera.SensorWidth, self._camera.SensorBits))
        self._logger.notice('Output format is %s' % self.pixelFormat())
        self._logger.notice('Exposure time is %f ms' % self.exposureTime())


    @synchronized("_mutex")
    def setStreamBytesPerSecond(self, streamBytesPerSecond):
        self._camera.StreamBytesPerSecond= streamBytesPerSecond
        self._logger.notice('Camera data rate set to %4.1f MB/s'
                            % (streamBytesPerSecond / 1e6))


    @override
    def setBinning(self, binning):
        self._binning= binning
        self._resetBinningAndOffset()


    @override
    def getBinning(self):
        return self._binning


    @synchronized("_mutex")
    def deviceModelName(self):
        return self._camera.DeviceModelName


    @synchronized("_mutex")
    def deviceID(self):
        return self._camera.DeviceID


    @override
    def name(self):
        return self._name


    @override
    @synchronized("_mutex")
    def rows(self):
        return self._camera.Height


    @override
    @synchronized("_mutex")
    def cols(self):
        return self._camera.Width


    @synchronized("_mutex")
    def bpp(self):
        return self._camera.SensorBits


    @synchronized("_mutex")
    def pixelFormat(self):
        return self._camera.PixelFormat


    @override
    def dtype(self):
        return self._dtype


    @override
    @synchronized("_mutex")
    def setExposureTime(self, exposureTimeInMilliSeconds):
        self._camera.ExposureTimeAbs= exposureTimeInMilliSeconds * 1000.


    @override
    @synchronized("_mutex")
    def exposureTime(self):
        return self._camera.ExposureTimeAbs / 1000.


    @override
    @synchronized("_mutex")
    def getFrameRate(self):
        return self._camera.AcquisitionFrameRateAbs


    @override
    @synchronized("_mutex")
    def setFrameRate(self, frameRate):
        self._camera.AcquisitionFrameRateAbs= np.minimum(
            frameRate, self._camera.AcquisitionFrameRateLimit)


    def readFrame(self, timeoutMilliSec=2000):
        pass


    def _notifyListenersAboutNewFrame(self):
        for callback in self._callbackList:
            callback(self._lastValidFrame)


    @synchronized("_mutex")
    def _frame_callback(self, frame):
        try:
            self._logger.debug("Got frame %d at time %.3f" % (
                self._counter, frame.getTimestamp() /
                self._timeStampTickFrequency))
            if frame.getReceiveStatus() == Vimba.FRAME_STATUS_COMPLETE:
                frame_data = frame.getBufferByteData()
                img = np.ndarray(buffer=frame_data,
                                 dtype=self._dtype,
                                 shape=(frame.height, frame.width))
                self._lastValidFrame= CameraFrame(img, counter=self._counter)
                self._notifyListenersAboutNewFrame()
                self._counter += 1
            else:
                self._logger.warn(
                    "Frame status not complete. "
                    "Try to reduce streamBytesPerSecond value")
            frame.queueFrameCapture(self._frame_callback)
        except Exception as e:
            self._logger.warn("Exception in handling frame callback: %s" %
                              str(e))


    def _createBufferPool(self):
        nVimbaFrames = 10
        self._frame_pool = [self._camera.getFrame() for _ in
                            np.arange(nVimbaFrames)]
        for frame in self._frame_pool:
            frame.announceFrame()
            frame.queueFrameCapture(self._frame_callback)


    def startAcquisition(self):
        self._createBufferPool()
        self._camera.startCapture()
        self._startImageAcquisition()


    def _startImageAcquisition(self):
        self._camera.AcquisitionMode= 'Continuous'
        self._camera.AcquisitionFrameRateAbs= \
            self._camera.AcquisitionFrameRateLimit
        self._camera.SyncOutSelector = 'SyncOut1'
        self._camera.SyncOutSource = 'Exposing'
        self._camera.TriggerSource = 'FixedRate'

        self._camera.runFeatureCommand('AcquisitionStart')
        self._logger.notice('Continuous acquisition started')
        self._isContinuouslyAcquiring= True


    def stopAcquisition(self):
        self._isContinuouslyAcquiring= False
        self._stopAcquisitionAndFlushQueue()
        time.sleep(0.2)
        self._revokeFrames()


    def _stopAcquisitionAndFlushQueue(self):
        self._camera.runFeatureCommand('AcquisitionStop')
        self._camera.flushCaptureQueue()
        self._camera.endCapture()


    def _revokeFrames(self):
        self._camera.revokeAllFrames()


    @synchronized("_mutex")
    def ipAddress(self):
        ip = self._camera.GevCurrentIPAddress
        return '.'.join([str(int('0x' + x, 16)) for x in reversed(
            textwrap.wrap(hex(ip), 2)[1:])])


    @synchronized("_mutex")
    def getCameraFeatures(self):
        res={}
        for featureName in self._camera.getFeatureNames():
            try:
                featureValue= self._camera.__getattr__(featureName)
            except Exception:
                featureValue= Vimba.NOT_AVAILABLE
            res[featureName]= featureValue
        return res


    @override
    def registerCallback(self, callback):
        self._callbackList.append(callback)


    @override
    def getFrameCounter(self):
        return self._counter


    @override
    def deinitialize(self):
        try:
            self._camera.closeCamera()
        except Exception:
            self._logger.warn('Failed to close camera')
