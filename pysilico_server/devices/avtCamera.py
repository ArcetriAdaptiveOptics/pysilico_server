#!/usr/bin/env python

import numpy as np
import textwrap
import threading
from plico.utils.decorator import logEnterAndExit, \
    synchronized, override
from pysilico_server.devices.abstract_camera import AbstractCamera
from plico.utils.logger import Logger
from pysilico.types.camera_frame import CameraFrame
from vimba import Vimba
import functools
from vimba.frame import PixelFormat, FrameStatus
from vimba.error import VimbaFeatureError


def withVimba():

    def wrapperFunc(f):

        @functools.wraps(f)
        def wrapper(self, *args, **kwds):
            with Vimba.get_instance():
                return f(self, *args, **kwds)

        return wrapper

    return wrapperFunc


def withCamera():

    def wrapperFunc(f):

        @functools.wraps(f)
        @withVimba()
        def wrapper(self, *args, **kwds):
            with self._camera:
                return f(self, *args, **kwds)

        return wrapper

    return wrapperFunc


class AvtCamera(AbstractCamera):

    VIMBA_BINNING_HORIZONTAL = "BinningHorizontal"
    VIMBA_BINNING_VERTICAL = "BinningVertical"
    VIMBA_DECIMATION_HORIZONTAL = 'DecimationHorizontal'
    VIMBA_DECIMATION_VERTICAL = 'DecimationVertical'
    VIMBA_FRAME_STATUS_COMPLETE = 0

    def __init__(self, vimbacamera, name):
        self._name = name
        self._camera = vimbacamera
        self._logger = Logger.of('AvtCamera')
        self._binning = 1
        self._counter = 0
        self._isContinuouslyAcquiring = False
        self._callbackList = []
        self._mutex = threading.RLock()
        self._lastValidFrame = CameraFrame(np.zeros((4, 4)), counter=0)
        self._initialize()

    @withVimba()
    def _initialize(self):

        # Limit data rate from camera
        try:
            streamBytesPerSecond = conf().getint('camera', 'streamBytesPerSecond')
        except:
            streamBytesPerSecond = 10000000
        self.setStreamBytesPerSecond(streamBytesPerSecond)

        self._resetBinningAndOffset()

        if self.pixelFormat() == PixelFormat.Mono12:
            self.BYTES_PER_PIXEL = 2
            self._dtype = np.uint16
        else:
            raise Exception('Format %s is not supported' % self.pixelFormat())

        self._logCameraInfo()
        self._logger.notice('AVT camera initialized')

    @logEnterAndExit('Entering _createFrames',
                     'Executed _createFrames',
                     'debug')
    @synchronized("_mutex")
    @withCamera()
    def _createFrames(self):
        # create new frames for the camera
        self._frame = self._camera.getFrame()  # creates a frame
        self._frame.announceFrame()

    def _isBinningAvailable(self):
        feat = list(self.getCameraFeatures().keys())
        return self.VIMBA_BINNING_HORIZONTAL in feat and \
            self.VIMBA_BINNING_VERTICAL in feat

    def _isDecimationAvailable(self):
        feat = list(self.getCameraFeatures().keys())
        return self.VIMBA_DECIMATION_HORIZONTAL in feat and \
            self.VIMBA_DECIMATION_VERTICAL in feat

    @synchronized("_mutex")
    @withCamera()
    def _resetBinningAndOffset(self):

        restartAcquistion = False
        if self._isContinuouslyAcquiring:
            self.stopAcquisition()
            restartAcquistion = True

        if self._isBinningAvailable():
            self._camera.BinningHorizontal.set(self._binning)
            self._camera.BinningVertical.set(self._binning)
        elif self._isDecimationAvailable():
            self._camera.DecimationHorizontal.set(self._binning)
            self._camera.DecimationVertical.set(self._binning)
        else:
            raise Exception("Neither binning nor decimation available")

        self._camera.OffsetX.set(0)
        self._camera.OffsetY.set(0)
        self._camera.Height.set(
            self._camera.SensorHeight.get() // self._binning)
        self._camera.Width.set(self._camera.SensorWidth.get() // self._binning)
        self._camera.set_pixel_format(PixelFormat.Mono12)
        self._camera.GVSPPacketSize.set(1500)
        # Not all cameras have this
        #self._timeStampTickFrequency = self._camera.GevTimestampTickFrequency.get()
        self._logger.notice(
            'Binning set to %d. Frame shape (w,h): (%d, %d) '
            'Left bottom pixel (%d, %d)'
            % (self._binning, self._camera.Width.get(),
               self._camera.Height.get(),
               self._camera.OffsetX.get(), self._camera.OffsetY.get()))

        if restartAcquistion:
            self.startAcquisition()

    @synchronized("_mutex")
    @withCamera()
    def _logCameraInfo(self):
        self._logger.notice('Camera: %s at %s - ID: %s' % (
                            self.deviceModelName(),
                            self.ipAddress(),
                            self.deviceID()))
        self._logger.notice('Sensor is %d rows x %d cols, %d bits/pixel' % (
            self._camera.SensorHeight.get(),
            self._camera.SensorWidth.get(), self._camera.SensorBits.get()))
        self._logger.notice('Output format is %s' % self.pixelFormat())
        self._logger.notice('Exposure time is %f ms' % self.exposureTime())

    @synchronized("_mutex")
    @withCamera()
    def setStreamBytesPerSecond(self, streamBytesPerSecond):
        try:
            self._camera.StreamBytesPerSecond.set(streamBytesPerSecond)
        except AttributeError:
            try:
                # Some cameras use a different name
                self._camera.DeviceLinkThroughputLimit.set(streamBytesPerSecond)
            except AttributeError:
                # If we can't set it, return silently and
                # avoid the logging notice
                return
        self._logger.notice('Camera data rate set to %4.1f MB/s'
                             % (streamBytesPerSecond / 1e6))

    @synchronized("_mutex")
    @withCamera()
    def getStreamBytesPerSecond(self):
        try:
            return self._camera.StreamBytesPerSecond.get()
        except AttributeError:
            # Some cameras do not have this attribute
            return 0

    @override
    def setBinning(self, binning):
        self._binning = binning
        self._resetBinningAndOffset()

    @override
    def getBinning(self):
        return self._binning

    @synchronized("_mutex")
    @withCamera()
    def deviceModelName(self):
        # return self._camera.DeviceModelName.get()
        return self._camera.get_model()

    @synchronized("_mutex")
    @withCamera()
    def deviceID(self):
        # return self._camera.DeviceID.get()
        return self._camera.get_id()

    @override
    def name(self):
        return self._name

    @override
    @synchronized("_mutex")
    @withCamera()
    def rows(self):
        return self._camera.Height.get()

    @override
    @synchronized("_mutex")
    @withCamera()
    def cols(self):
        return self._camera.Width.get()

    @synchronized("_mutex")
    @withCamera()
    def bpp(self):
        return self._camera.SensorBits.get()

    @synchronized("_mutex")
    @withCamera()
    def pixelFormat(self):
        return self._camera.get_pixel_format()

    @override
    def dtype(self):
        return self._dtype

    @override
    @synchronized("_mutex")
    @withCamera()
    def setExposureTime(self, exposureTimeInMilliSeconds):
        try:
            self._camera.ExposureTimeAbs.set(exposureTimeInMilliSeconds * 1000.)
        except AttributeError:
            # Some cameras use ExposureTime, others ExposureTimeAbs. We try both.
            self._camera.ExposureTime.set(exposureTimeInMilliSeconds * 1000.)
        self._logger.notice('Exposure time set to %g ms' % (
            exposureTimeInMilliSeconds))

    @override
    @synchronized("_mutex")
    @withCamera()
    def exposureTime(self):
        try:
            return self._camera.ExposureTimeAbs.get() / 1000.
        except AttributeError:
            # Some cameras use ExposureTime, others ExposureTimeAbs. We try both.
            return self._camera.ExposureTime.get() / 1000.

    @override
    @synchronized("_mutex")
    @withCamera()
    def getFrameRate(self):
        try:
            return self._camera.AcquisitionFrameRateAbs.get()
        except AttributeError:
            # Some cameras use AcquisitionFrameRate, others AcquisitionFrameRateAbs. We try both.
            return self._camera.AcquisitionFrameRate.get()

    @override
    @synchronized("_mutex")
    @withCamera()
    def setFrameRate(self, frameRate):
        try:
            self._camera.AcquisitionFrameRateAbs.set(np.minimum(
                frameRate,
                self._maximum_frame_rate()))
        except AttributeError:
            # Some cameras use AcquisitionFrameRate, others AcquisitionFrameRateAbs. We try both.
            self._camera.AcquisitionFrameRate.set(np.minimum(
                frameRate,
                self._maximum_frame_rate()))
        self._logger.notice('Frame rate set to %g Hz - (requested %g Hz)'
                            % (self.getFrameRate(), frameRate))

    def readFrame(self, timeoutMilliSec=2000):
        pass

    def _notifyListenersAboutNewFrame(self):
        for callback in self._callbackList:
            callback(self._lastValidFrame)

    def _frame_callback(self, camera, frame):
        try:
            # self._logger.debug("Got frame %d at time %.3f" % (
            #    self._counter, frame.get_timestamp() /
            #    self._timeStampTickFrequency))
            if frame.get_status() == FrameStatus.Complete:
                frame_data = frame.get_buffer()
                img = np.ndarray(buffer=frame_data,
                                 dtype=self._dtype,
                                 shape=(frame.get_height(), frame.get_width()))
                self._lastValidFrame = CameraFrame(img, counter=self._counter)
                self._notifyListenersAboutNewFrame()
                self._counter += 1
            else:
                self._logger.warn(
                    "Frame status not complete. "
                    "Try to reduce streamBytesPerSecond value")
            camera.queue_frame(frame)
        except Exception as e:
            self._logger.warn("Exception in handling frame callback: %s" %
                              str(e))

    @withCamera()
    def _adjust_packet_size(self):
        try:
            self._camera.GVSPAdjustPacketSize.run()

            while not self._camera.GVSPAdjustPacketSize.is_done():
                pass

        except (AttributeError, VimbaFeatureError):
            pass

    def _maximum_frame_rate(self):
        aLittleBitSlower = 0.01
        return self._camera.AcquisitionFrameRateLimit.get() - aLittleBitSlower

    @withCamera()
    def startAcquisition(self):
        self._adjust_packet_size()
        self._camera.TriggerSelector.set('FrameStart')
        self._camera.TriggerSource.set('FixedRate')
        self._camera.AcquisitionMode.set('Continuous')
        self.setFrameRate(self._maximum_frame_rate())
        try:
            self._camera.SyncOutSelector.set('SyncOut1')
            self._camera.SyncOutSource.set('Exposing')
        except AttributeError:
            pass
        self._camera.start_streaming(
            handler=self._frame_callback, buffer_count=10)
        self._logger.notice('Continuous acquisition started')
        self._isContinuouslyAcquiring = True

    @withCamera()
    def stopAcquisition(self):
        self._isContinuouslyAcquiring = False
        # self._stopAcquisitionAndFlushQueue()
        # time.sleep(0.2)
        # self._revokeFrames()
        self._camera.stop_streaming()

    @withCamera()
    def _stopAcquisitionAndFlushQueue(self):
        self._camera.runFeatureCommand('AcquisitionStop')
        self._camera.flushCaptureQueue()
        self._camera.endCapture()

    @withCamera()
    def _revokeFrames(self):
        self._camera.revokeAllFrames()

    @synchronized("_mutex")
    @withCamera()
    def ipAddress(self):
        ip = self._camera.GevCurrentIPAddress.get()
        return '.'.join([str(int('0x' + x, 16)) for x in reversed(
            textwrap.wrap(hex(ip), 2)[1:])])

    @synchronized("_mutex")
    @withCamera()
    def getCameraFeatures(self):
        res = {}
        for feature in self._camera.get_all_features():
            try:
                featureName = feature.get_name()
                featureValue = feature.get()
            except Exception:
                featureValue = None
            res[featureName] = featureValue
        return res

    @override
    def registerCallback(self, callback):
        self._callbackList.append(callback)

    @override
    def getFrameCounter(self):
        return self._counter

    @override
    @withCamera()
    def deinitialize(self):
        try:
            self.stopAcquisition()
            # There is no closeCamera() method apparently
            # self._camera.closeCamera()
        except Exception as e:
            self._logger.warn('Failed to close camera:'+str(e))
