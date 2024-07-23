import threading
import traceback
import numpy as np
from pypylon import pylon, genicam
from pysilico_server.devices.abstract_camera import AbstractCamera, CameraException
from pysilico.types.camera_frame import CameraFrame
from plico.utils.decorator import override, synchronized
from plico.utils.logger import Logger


class ImageHandler(pylon.ImageEventHandler):
    def __init__(self, basler_camera, mutex):
        super().__init__()
        self._basler_camera = basler_camera
        self._mutex = mutex

    @synchronized("_mutex")
    def OnImageGrabbed(self, camera, grabResult):
        try:
            if not grabResult.GrabSucceeded():
                return self._basler_camera._logger.warn("Frame grab not successful")
            elif not grabResult.IsValid():
                return self._basler_camera._logger.warn("Frame grab is not valid")
            else:
                self._basler_camera._lastValidFrame = CameraFrame(grabResult.Array, counter=self._basler_camera._counter)
                self._basler_camera._notifyListenersAboutNewFrame()
                self._basler_camera._counter += 1
        except Exception as e:
            self._basler_camera._logger.warn("Exception in handling frame callback: %s" %str(e))

# def withCamera(f):
    
#     @functools.wraps(f)
#     def wrapper(self, *args, **kwds):
#         self._camera.Open()
#         res = f(self, *args, **kwds)
#         self._camera.Close()
#         return res

#     return wrapper


def get_device_by_ip(ip_address):
    factory = pylon.TlFactory.GetInstance()
    devices = factory.EnumerateDevices()
    for d in devices:
        if d.GetIpAddress() == ip_address:
            return pylon.InstantCamera(factory.CreateDevice(d))
    raise ValueError('Camera with IP address %s not found' %ip_address)

class BaslerCamera(AbstractCamera):

    def __init__(self, camera, name):
        self._camera = camera
        self._name = name
        self._counter = 0
        self._logger = Logger.of('BaslerCamera')
        self._mutex = threading.RLock()
        self._handler = ImageHandler(self, self._mutex)
        self._lastValidFrame = CameraFrame(np.zeros((4, 4)), counter=0)
        self._callbackList = []
        self._initialize()

    @synchronized("_mutex")
    def _initialize(self):
        self._camera.RegisterImageEventHandler(self._handler,
                                               pylon.RegistrationMode_Append,
                                               pylon.Cleanup_Delete)
        self._camera.Open()
        self._logCameraInfo()
        self._logger.notice('Basler camera initialized')
        self._dtype = np.uint(16)

    def _logCameraInfo(self):
        self._logger.notice('Camera: %s at %s - ID: %s' % (
                            self.deviceModelName(),
                            self.ipAddress(),
                            self.deviceID()))
        self._logger.notice('Sensor is %d rows x %d cols' % (
            self.rows(),
            self.cols()))
        self._logger.notice('Output format is %s' % self.pixelFormat())
        self._logger.notice('Exposure time is %f ms' % self.exposureTime())

    @override
    def name(self):
        return self._name
    
    @synchronized("_mutex")
    def deviceModelName(self):
        return self._camera.DeviceInfo.GetModelName()
    
    @synchronized("_mutex")
    def deviceID(self):
        return self._camera.DeviceID()
    
    @synchronized("_mutex")
    def ipAddress(self):
        return self._camera.DeviceInfo.GetIpAddress()

    @override
    #@returns(numpy.ndarray)
    def readFrame(self, timeoutMilliSec=2000):
        pass
    
    @synchronized("_mutex")
    @override
    def rows(self):
        return self._camera.Height()

    @synchronized("_mutex")
    @override
    def cols(self):
        return self._camera.Width()

    @override
    def dtype(self):
        return self._dtype

    @synchronized("_mutex")
    @override
    def setExposureTime(self, exposureTimeInMilliSeconds):
        self._camera.ExposureTimeAbs.SetValue(exposureTimeInMilliSeconds*1e3)
        self._logger.notice('Exposure time set to %g ms' % (exposureTimeInMilliSeconds))

    @synchronized("_mutex")
    @override
    def exposureTime(self):
        try:
            return self._camera.ExposureTimeAbs() * 1e-3
        except genicam.RuntimeException as e:
            self._logger.warn('Unhandled exception: '+str(e))
            traceback.print_exc()
            raise CameraException(str(e)) 
    
    @synchronized("_mutex")
    def pixelFormat(self):
        return self._camera.PixelFormat()

    @synchronized("_mutex")
    @override
    def setBinning(self, binning):
        self._camera.BinningHorizontal.SetValue(binning)
        self._camera.BinningVertical.SetValue(binning)

    @synchronized("_mutex")
    @override
    def getBinning(self):
        return self._camera.BinningHorizontal.GetValue()

    @override
    def registerCallback(self, callback):
        self._callbackList.append(callback)

    @synchronized("_mutex")
    @override
    def startAcquisition(self):
        self._camera.UserSetSelector.SetValue("Default")
        self._camera.UserSetLoad.Execute()
        self._camera.TriggerSelector.SetValue("FrameStart")
        self._camera.PixelFormat.SetValue("Mono10p")
        self._camera.AcquisitionMode.SetValue("Continuous")
        self._camera.GevSCPD.SetValue(1500)
        self._camera.TriggerMode.SetValue("Off")
        self._camera.StartGrabbing(pylon.GrabStrategy_LatestImages, pylon.GrabLoop_ProvidedByInstantCamera)
        self._logger.notice('Continuous acquisition started')

    @synchronized("_mutex")
    @override
    def stopAcquisition(self):
        self._camera.StopGrabbing()

    @override
    def getFrameCounter(self):
        return self._counter

    @synchronized("_mutex")
    @override
    def getFrameRate(self):
        return self._camera.AcquisitionFrameRateAbs()

    @synchronized("_mutex")
    @override
    def setFrameRate(self, frameRateInHz):
        self._camera.AcquisitionFrameRateEnable.Value = True
        self._camera.AcquisitionFrameRateAbs.SetValue(frameRateInHz)
    
    @synchronized("_mutex")
    @override
    def deinitialize(self):
        try:
            self.stopAcquisition()
        except Exception as e:
            self._logger.warn('Failed to close camera:'+str(e))
        self._camera.Close()

    def _notifyListenersAboutNewFrame(self):
        for callback in self._callbackList:
            callback(self._lastValidFrame)

    @override
    def setParameter(self, name, value):
        pass

    @override
    def getParameters(self):
        return {}
