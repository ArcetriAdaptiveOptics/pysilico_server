
from pypylon import pylon
from pysilico_server.devices.abstract_camera import AbstractCamera
from plico.utils.decorator import override
import functools

# class SampleImageEventHandler(pylon.ImageEventHandler):
#     def __init__(self, baslerCamera):
#         super().__init__()
#         self._baslerCamera = baslerCamera

#     def OnImageGrabbed(self, camera, grabResult):
#         self._baslerCamera._lastValidFrame = grabResult.Array
#         self._baslerCamera._notifyListenersAboutNewFrame()

def withCamera():

    def wrapperFunc(f):

        @functools.wraps(f)
        def wrapper(self, *args, **kwds):
            self._camera.Open()
            res = f(self, *args, **kwds) 
            self._camera.Close()
            return res

        return wrapper

    return wrapperFunc


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
        #self._camera.Open()
        self._callbackList = []
        #self._handler = SampleImageEventHandler(self)
        # self._camera.RegisterImageEventHandler(self._handler,
        #                                        pylon.RegistrationMode_Append,
        #                                        pylon.Cleanup_Delete)

    @override
    def name(self):
        return self._name

    @override
    #@returns(numpy.ndarray)
    def readFrame(self, timeoutMilliSec=2000):
        assert False

    @override
    def rows(self):
        return self._camera.Height.GetValue()

    @override
    def cols(self):
        return self._camera.Width.GetValue()

    @override
    def dtype(self):
        assert False

    @override
    @withCamera()
    def setExposureTime(self, exposureTimeInMilliSeconds):
        self._camera.ExposureTimeAbs.SetValue(exposureTimeInMilliSeconds*1e3)

    @override
    @withCamera()
    def exposureTime(self):
        return self._camera.ExposureTimeAbs.GetValue()

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
        self._camera.Open()
        self._camera.UserSetSelector.SetValue("Default")
        self._camera.UserSetLoad.Execute()
        self._camera.TriggerSelector.SetValue("FrameStart")
        self._camera.PixelFormat.SetValue("Mono10")
        self._camera.AcquisitionMode.SetValue("Continuous")
        self._camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)

    @override
    def stopAcquisition(self):
        #TODO: check if better in deinitialize()
        self._camera.Close()

    @override
    def getFrameCounter(self):
        assert False

    @override
    def deinitialize(self):
        assert False

    def _notifyListenersAboutNewFrame(self):
        for callback in self._callbackList:
            callback(self._lastValidFrame)
