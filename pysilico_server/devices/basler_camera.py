import numpy as np
from pypylon import pylon, genicam
from pysilico_server.devices.abstract_camera import AbstractCamera
from pysilico.types.camera_frame import CameraFrame
from plico.utils.decorator import override
import functools
import time


class ImageHandler(pylon.ImageEventHandler):
    def __init__(self, basler_camera):
        super().__init__()
        self._basler_camera = basler_camera

    def OnImageGrabbed(self, camera, grabResult):
        print("CSampleImageEventHandler::OnImageGrabbed called.")
        self._basler_camera._lastValidFrame = grabResult.Array
        self._basler_camera._notifyListenersAboutNewFrame()

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
        self._handler = ImageHandler(self)
        self._lastValidFrame = CameraFrame(np.zeros((4, 4)), counter=0)
        self._camera.RegisterImageEventHandler(self._handler,
                                               pylon.RegistrationMode_Append,
                                               pylon.Cleanup_Delete)
        self._camera.Open()
        self._callbackList = []

    @override
    def name(self):
        return self._name

    @override
    #@returns(numpy.ndarray)
    def readFrame(self, timeoutMilliSec=2000):
        assert False

    @override
    def rows(self):
        return self._camera.Height()

    @override
    def cols(self):
        return self._camera.Width()

    @override
    def dtype(self):
        assert False

    @override
    def setExposureTime(self, exposureTimeInMilliSeconds):
        self._camera.ExposureTimeAbs.SetValue(exposureTimeInMilliSeconds*1e3)

    @override
    def exposureTime(self):
        return self._camera.ExposureTimeAbs()

    @override
    def setBinning(self, binning):
        '''
        Parameters
        ----------
        binning: tuple
            Horizontal and vertical binning.
        '''
        self._camera.BinningHorizontal.SetValue(binning[0])
        self._camera.BinningVertical.SetValue(binning[1])

    @override
    def getBinning(self):
        return (self._camera.BinningHorizontal.GetValue(),
                self._camera.BinningVertical.GetValue())

    @override
    def registerCallback(self, callback):
        self._callbackList.append(callback)

    @override
    def startAcquisition(self):
        self._camera.UserSetSelector.SetValue("Default")
        self._camera.UserSetLoad.Execute()
        self._camera.TriggerSelector.SetValue("FrameStart")
        self._camera.PixelFormat.SetValue("Mono10")
        self._camera.AcquisitionMode.SetValue("Continuous")
        self._camera.TriggerMode.SetValue("Off")
        self._camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly, pylon.GrabLoop_ProvidedByInstantCamera)

    @override
    def stopAcquisition(self):
        self._camera.StopGrabbing()

    @override
    def getFrameCounter(self):
        assert False

    @override
    def deinitialize(self):
        self._camera.Close()

    def _notifyListenersAboutNewFrame(self):
        for callback in self._callbackList:
            callback(self._lastValidFrame)


# def main_on_grabbing_techniques():
#     cam = get_device_by_ip('193.206.155.38')
#     cam.Open()
#     print('ONE BY ONE:')
#     cam.MaxNumBuffer.Value = 15
#     cam.StartGrabbing(pylon.GrabStrategy_OneByOne)
#     print('MaxNumBuffer set = %s' %cam.MaxNumBuffer.Value)
#     print('Output queue size = %s' %cam.OutputQueueSize())
#     cam.StopGrabbing()
#     print('\nLATEST IMAGE ONLY:')
#     cam.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
#     print('\nMaxNumBuffer set = %s' %cam.MaxNumBuffer.Value)
#     print('Output queue size = %s' %cam.OutputQueueSize())
#     cam.StopGrabbing()
#     print('\nLATEST IMAGES:')
#     cam.StartGrabbing(pylon.GrabStrategy_LatestImages)
#     print('\nMaxNumBuffer set = %s' %cam.MaxNumBuffer.Value)
#     print('Output queue size = %s' %cam.OutputQueueSize())
#     cam.StopGrabbing()
#     cam.Close()


# def main_on_latest_images_technique():
#     cam = get_device_by_ip('193.206.155.38')
#     cam.Open()
#     print('MaxNumBuffer set = %s' %cam.MaxNumBuffer.Value)
#     print('Output queue size set = %s' %cam.OutputQueueSize())
#     cam.StartGrabbingMax(30, pylon.GrabStrategy_LatestImages)
#     buffersInQueue = 0
#     while cam.RetrieveResult(2000, pylon.TimeoutHandling_Return):
#         buffersInQueue += 1
#         print(buffersInQueue)
#     print('Buffers in queue: %s' %buffersInQueue)
#     print('Output queue size = %s' %cam.OutputQueueSize())
#     cam.StopGrabbing()
#     cam.OutputQueueSize.Value = 20
#     cam.StartGrabbingMax(30, pylon.GrabStrategy_LatestImages)
#     print('Changed output queue size = 20')
#     buffersInQueue = 0
#     while cam.RetrieveResult(2000, pylon.TimeoutHandling_Return):
#         buffersInQueue += 1
#         print(buffersInQueue)
#     print('Buffers in queue: %s' %buffersInQueue)
#     cam.StopGrabbing()
#     cam.Close()


# def main_on_camera_event_handler():
#     cam = get_device_by_ip('193.206.155.38')
#     # camera_handler = CameraHandler()
#     # cam.RegisterConfiguration(pylon.SoftwareTriggerConfiguration(),
#     #                           pylon.RegistrationMode_ReplaceAll, pylon.Cleanup_Delete) 
#     # cam.GrabCameraEvents = True
#     # cam.RegisterCameraEventHandler(camera_handler, "ExposureEndEventData", 
#     #                           100, pylon.RegistrationMode_Append,
#     #                           pylon.Cleanup_None)
#     cam.RegisterImageEventHandler(ImageHandler(), pylon.RegistrationMode_Append,
#                                   pylon.Cleanup_Delete)
#     try:
#         cam.Open()
#         cam.TriggerSelector.SetValue("FrameStart")
#         cam.AcquisitionMode.SetValue("Continuous")
#         cam.TriggerMode.SetValue("Off")
#         if not genicam.IsAvailable(cam.EventSelector):
#             raise genicam.RuntimeException("The device doesn't support events.")
        
#         # cam.EventSelector.Value = "ExposureEnd"
#         # cam.EventNotification.Value = "On"
        
#         print(cam.MaxNumBuffer())
#         print(cam.OutputQueueSize())
#         cam.StartGrabbing(pylon.GrabStrategy_LatestImageOnly,
#                             pylon.GrabLoop_ProvidedByInstantCamera)
#         time.sleep(5)
#         cam.Close()
#         time.sleep(5)
#     finally:
#         cam.Open()
#         cam.StopGrabbing()
#         cam.Close()
    
