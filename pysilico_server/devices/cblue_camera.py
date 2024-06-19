import threading
import FliSdk_V2
from pysilico_server.devices.abstract_camera import AbstractCamera
from plico.utils.logger import Logger
from plico.utils.decorator import synchronized, override

# class ImageHandler(pylon.ImageEventHandler):
#     def __init__(self, basler_camera, mutex):
#         super().__init__()
#         self._basler_camera = basler_camera
#         self._mutex = mutex

#     @synchronized("_mutex")
#     def OnImageGrabbed(self, camera, grabResult):
#         try:
#             if not grabResult.GrabSucceeded():
#                 return self._basler_camera._logger.warn("Frame grab not successful")
#             elif not grabResult.IsValid():
#                 return self._basler_camera._logger.warn("Frame grab is not valid")
#             else:
#                 self._basler_camera._lastValidFrame = CameraFrame(grabResult.Array, counter=self._basler_camera._counter)
#                 self._basler_camera._notifyListenersAboutNewFrame()
#                 self._basler_camera._counter += 1
#         except Exception as e:
#             self._basler_camera._logger.warn("Exception in handling frame callback: %s" %str(e))


# def get_device_by_ip(ip_address):
#     factory = pylon.TlFactory.GetInstance()
#     devices = factory.EnumerateDevices()
#     for d in devices:
#         if d.GetIpAddress() == ip_address:
#             return pylon.InstantCamera(factory.CreateDevice(d))
#     raise ValueError('Camera with IP address %s not found' %ip_address)

class CblueOneSfncCamera(AbstractCamera):

    def __init__(self, name):
        self._context = FliSdk_V2.Init()
        self._find_camera()
        self._set_camera()
        # self._camera = camera
        self._name = name
        # self._counter = 0
        self._logger = Logger.of('CblueOneSfncCamera')
        self._mutex = threading.RLock()
        # self._handler = ImageHandler(self, self._mutex)
        # self._lastValidFrame = CameraFrame(np.zeros((4, 4)), counter=0)
        # self._callbackList = []
        # self._initialize()
        

    def _find_camera(self):
        # self._logger.notice('Detection of grabbers...')
        self._grabbers = FliSdk_V2.DetectGrabbers(self._context)
        if len(self._grabbers) == 0:
            raise Exception('No grabber detected, exit.')
        # self._logger.notice('Done.')
        # self._logger.notice('List of detected grabber(s):')
        # for s in self._grabbers:
        #     self._logger.notice("- " + s)

        # self._logger.notice('Detection of cameras...')
        self._cameras = FliSdk_V2.DetectCameras(self._context)
        if len(self._cameras) == 0:
            raise Exception('No camera detected, exit.')
        # self._logger.notice('Done.')
        # self._logger.notice('List of detected camera(s):')
        # for s in self._cameras:
            # self._logger.notice("- " + s)       

    def _set_camera(self, camera_idx=0):
        if camera_idx is None:
            camera_idx = int(input('Which camera to use? (0, 1, ...) '))
        ok = FliSdk_V2.SetCamera(self._context, self._cameras[camera_idx])
        result = FliSdk_V2.SetMode(self._context, FliSdk_V2.Mode.Full)
        # self._logger.notice(f'Setting mode full:{result}')

        ok = FliSdk_V2.Update(self._context)
        if not ok:
            raise Exception('Error while updating SDK')
        is_cblue = FliSdk_V2.IsCblueSfnc(self._context)
        # self._logger.notice(f'IsCblueOneSfnc: {is_cblue}')
        result = FliSdk_V2.GetCameraModel(self._context)
        # self._logger.notice(f'GetCameraModel: {result}')
        result = FliSdk_V2.GetCurrentCameraName(self._context)
        # self._logger.notice(f'GetCurrentCameraName: {result}')



    # @synchronized("_mutex")
    # def _initialize(self):

    #     self._camera.RegisterImageEventHandler(self._handler,
    #                                            pylon.RegistrationMode_Append,
    #                                            pylon.Cleanup_Delete)
    #     self._camera.Open()
    #     self._logCameraInfo()
    #     self._logger.notice('Basler camera initialized')
    #     self._dtype = np.uint(16)

    # def _logCameraInfo(self):
    #     self._logger.notice('Camera: %s at %s - ID: %s' % (
    #                         self.deviceModelName(),
    #                         self.ipAddress(),
    #                         self.deviceID()))
    #     self._logger.notice('Sensor is %d rows x %d cols' % (
    #         self.rows(),
    #         self.cols()))
    #     self._logger.notice('Output format is %s' % self.pixelFormat())
    #     self._logger.notice('Exposure time is %f ms' % self.exposureTime())

    @override
    def name(self):
        return self._name
    
    @synchronized("_mutex")
    def deviceModelName(self):
        return FliSdk_V2.FliCblueSfnc.GetDeviceModelName(self._context)[1]
    
    # @synchronized("_mutex")
    # def deviceID(self):
    #     return self._camera.DeviceID()
    
    # @synchronized("_mutex")
    # def ipAddress(self):
    #     return self._camera.DeviceInfo.GetIpAddress()

    @override
    #@returns(numpy.ndarray)
    def readFrame(self, timeoutMilliSec=2000):
        pass
    
    @synchronized("_mutex")
    @override
    def rows(self):
        return FliSdk_V2.FliCblueSfnc.GetHeight(self._context)[1]

    @synchronized("_mutex")
    @override
    def cols(self):
        return FliSdk_V2.FliCblueSfnc.GetWidth(self._context)[1]
    
    def set_rows(self, rows_in_px):
        ok = FliSdk_V2.FliCblueSfnc.SetHeight(self._context, rows_in_px)

    def set_cols(self, cols_in_px):
        ok = FliSdk_V2.FliCblueSfnc.SetWidth(self._context, cols_in_px)

    @override
    def dtype(self):
        pass

    @synchronized("_mutex")
    @override
    def setExposureTime(self, exposureTimeInMilliSeconds):
        exp_time_max_ms = FliSdk_V2.FliCblueSfnc.GetExposureTimeMax(self._context)[1] * 1e-3
        exp_time_min_ms = FliSdk_V2.FliCblueSfnc.GetExposureTimeMin(self._context)[1] * 1e-3
        if exposureTimeInMilliSeconds < exp_time_min_ms or exposureTimeInMilliSeconds > exp_time_max_ms:
            raise ValueError(f'Exposure time must be in the range {exp_time_min_ms, exp_time_max_ms} ms') 

        ok = FliSdk_V2.FliCblueSfnc.SetExposureTime(self._context, exposureTimeInMilliSeconds*1e3)
        # self._logger.notice(f'Exposure time set to {exposureTimeInMilliSeconds} ms')

    @synchronized("_mutex")
    @override
    def exposureTime(self):
        result = FliSdk_V2.FliCblueSfnc.GetExposureTime(self._context)
        return result[1] * 1e-3
        
    # @synchronized("_mutex")
    # def pixelFormat(self):
    #     return self._camera.PixelFormat()

    @synchronized("_mutex")
    @override
    def setBinning(self, binning):
        pass

    @synchronized("_mutex")
    @override
    def getBinning(self):
        pass

    @override
    def registerCallback(self, callback):
        pass
        # self._callbackList.append(callback)

    @synchronized("_mutex")
    @override
    def startAcquisition(self):
        
    #     self._camera.UserSetSelector.SetValue("Default")
    #     self._camera.UserSetLoad.Execute()
    #     self._camera.TriggerSelector.SetValue("FrameStart")
    #     self._camera.PixelFormat.SetValue("Mono10p")
    #     self._camera.AcquisitionMode.SetValue("Continuous")
    #     self._camera.GevSCPD.SetValue(1500)
    #     self._camera.TriggerMode.SetValue("Off")
    #     self._camera.StartGrabbing(pylon.GrabStrategy_LatestImages, pylon.GrabLoop_ProvidedByInstantCamera)
    #     self._logger.notice('Continuous acquisition started')

    @synchronized("_mutex")
    @override
    def stopAcquisition(self):
        pass
        # self._camera.StopGrabbing()

    @override
    def getFrameCounter(self):
        pass
        # return self._counter

    @synchronized("_mutex")
    @override
    def getFrameRate(self):
        return FliSdk_V2.FliCblueSfnc.GetAcquisitionFrameRate(self._context)[1]

    @synchronized("_mutex")
    @override
    def setFrameRate(self, frameRateInHz):
        ok = FliSdk_V2.FliCblueSfnc.SetAcquisitionFrameRate(self._context, frameRateInHz)
        # self._logger.notice(f'Acquisition frame rate set to {frameRateInHz} Hz')
    
    @synchronized("_mutex")
    @override
    def deinitialize(self):
        pass
        # try:
        #     self.stopAcquisition()
        # except Exception as e:
        #     self._logger.warn('Failed to close camera:'+str(e))
        # self._camera.Close()

    # def _notifyListenersAboutNewFrame(self):
    #     for callback in self._callbackList:
    #         callback(self._lastValidFrame)