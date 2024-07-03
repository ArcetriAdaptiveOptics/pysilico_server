import functools
import time
import threading
import FliSdk_V2
import CblueOne_enum as CblueOne
from pysilico_server.devices.abstract_camera import AbstractCamera
from pysilico.types.camera_frame import CameraFrame
from plico.utils.logger import Logger
from plico.utils.decorator import synchronized, override


def stop_start(f):

    @functools.wraps(f)
    def wrapper(self, *args, **kwargs):
        FliSdk_V2.Stop(self._context)
        res = f(self, *args, **kwargs)
        FliSdk_V2.Start(self._context)
        return res
    
    return wrapper

class RepeatTimer(threading.Timer):
    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)


class CblueOneCamera(AbstractCamera):

    def __init__(self, name):
        self._logger = Logger.of('CblueOneCamera')
        self._context = FliSdk_V2.Init()
        self._find_camera()
        self._set_camera(name)
        self._name = name
        self._mutex = threading.RLock()
        self._timer = RepeatTimer(0.005, self.callback_timer)
        self._callbackList = []
        self._timer.start()
        self._lastIndex = 0

    def _find_camera(self):
        self._logger.notice('Detection of grabbers...')
        self._grabbers = FliSdk_V2.DetectGrabbers(self._context)
        if len(self._grabbers) == 0:
            raise Exception('No grabber detected, exit.')
        self._logger.notice('Done.')
        self._logger.notice('List of detected grabber(s):')
        for s in self._grabbers:
            self._logger.notice("- " + s)

        self._logger.notice('Detection of cameras...')
        self._cameras = FliSdk_V2.DetectCameras(self._context)
        if len(self._cameras) == 0:
            raise Exception('No camera detected, exit.')
        self._logger.notice('Done.')
        self._logger.notice('List of detected camera(s):')
        for s in self._cameras:
            self._logger.notice("- " + s)       

    def _set_camera(self, camera_name):
        ok = FliSdk_V2.SetCamera(self._context, camera_name)
        result = FliSdk_V2.SetMode(self._context, FliSdk_V2.Mode.Full)
        self._logger.notice(f'Setting mode full:{result}')
        ok = FliSdk_V2.Update(self._context)
        if not ok:
            raise Exception('Error while updating SDK')
        is_cblue = FliSdk_V2.IsCblueSfnc(self._context)
        self._logger.notice(f'IsCblueOneSfnc: {is_cblue}')
        result = FliSdk_V2.GetCameraModel(self._context)
        self._logger.notice(f'GetCameraModel: {result}')
        result = FliSdk_V2.GetCurrentCameraName(self._context)
        self._logger.notice(f'GetCurrentCameraName: {result}')
        self.set_device_cooling_setpoint(10)
        self.set_conversion_efficiency(CblueOne.ConversionEfficiency.Low)
        self.set_gain(0)

    def callback_timer(self):
        frame = self.readFrame()
        cameraFrame = CameraFrame(frame, counter=self.getFrameCounter())
        for callback in self._callbackList:
            callback(cameraFrame)
        self._logger.notice(f'New camera frame: {id(cameraFrame)}')

    @override
    def name(self):
        return self._name
    
    @synchronized("_mutex")
    def device_model_name(self):
        return FliSdk_V2.FliCblueSfnc.GetDeviceModelName(self._context)[1]

    @override
    #@returns(numpy.ndarray)
    def readFrame(self, timeoutMilliSec=2000):
        frame = self.getFrame(next=True, timeout=timeoutMilliSec/1000)
        return frame

    def getFrame(self, index=-1, next=False, timeout=1):

        if next is True:
             start = time.time()
             index = self.getFrameCounter()
             while index == self._lastIndex:
                  if time.time()-start > timeout:
                      raise TimeoutError('Timeout waiting for Ocam2K frames')
                  index = self.getFrameCounter()
             self._lastIndex = index
 
        return FliSdk_V2.GetRawImageAsNumpyArray(self._context, index)
    
    @synchronized("_mutex")
    @override
    def rows(self):
        return FliSdk_V2.FliCblueSfnc.GetHeight(self._context)[1]

    @synchronized("_mutex")
    @override
    def cols(self):
        return FliSdk_V2.FliCblueSfnc.GetWidth(self._context)[1]
    
    @synchronized("_mutex")
    @stop_start
    def set_rows(self, rows_in_px):
        ok = FliSdk_V2.FliCblueSfnc.SetHeight(self._context, rows_in_px)

    @synchronized("_mutex")
    @stop_start
    def set_cols(self, cols_in_px):
        ok = FliSdk_V2.FliCblueSfnc.SetWidth(self._context, cols_in_px)

    @synchronized("_mutex")
    @stop_start
    def get_rows_max(self):
        ok = FliSdk_V2.FliCblueSfnc.GetHeightMax(self._context)

    @synchronized("_mutex")
    @stop_start
    def get_cols_max(self):
        ok = FliSdk_V2.FliCblueSfnc.GetWidthMax(self._context)

    @override
    def dtype(self):
        pass

    @stop_start
    def set_device_cooling_setpoint(self, temperature_in_celsius):
        if not FliSdk_V2.FliCblueOne.GetDeviceCoolingEnable(self._context):
            ok = FliSdk_V2.FliCblueOne.SetDeviceCoolingEnable(self._context, True)
        ok = FliSdk_V2.FliCblueOne.SetDeviceCoolingSetpoint(self._context, temperature_in_celsius)
        self._logger.notice(f'Set device cooling setpoint to: {self.get_device_cooling_setpoint()} degrees Celsius')

    @synchronized("_mutex")
    def get_device_cooling_enable(self):
        return FliSdk_V2.FliCblueOne.GetDeviceCoolingEnable(self._context)[1]

    def get_device_cooling_setpoint(self):
        return FliSdk_V2.FliCblueOne.GetDeviceCoolingSetpoint(self._context)[1]
    
    @synchronized("_mutex")
    def get_device_temperature(self):
        return FliSdk_V2.FliCblueSfnc.GetDeviceTemperature(self._context)[1]

    @synchronized("_mutex")
    @override
    @stop_start
    def setExposureTime(self, exposureTimeInMilliSeconds):
        exp_time_max_ms = FliSdk_V2.FliCblueSfnc.GetExposureTimeMax(self._context)[1] * 1e-3
        exp_time_min_ms = FliSdk_V2.FliCblueSfnc.GetExposureTimeMin(self._context)[1] * 1e-3
        if exposureTimeInMilliSeconds < exp_time_min_ms or exposureTimeInMilliSeconds > exp_time_max_ms:
            raise ValueError(f'Exposure time must be in the range {exp_time_min_ms, exp_time_max_ms} ms') 

        ok = FliSdk_V2.FliCblueSfnc.SetExposureTime(self._context, exposureTimeInMilliSeconds*1e3)
        self._logger.notice(f'Exposure time set to {exposureTimeInMilliSeconds} ms')

    @synchronized("_mutex")
    @override
    def exposureTime(self):
        result = FliSdk_V2.FliCblueSfnc.GetExposureTime(self._context)
        return result[1] * 1e-3

    @synchronized("_mutex")
    @override
    def setBinning(self, binning):
        if self.device_model_name() == 'C-BLUE ONE 1.7 MP':
            raise ValueError('C-Blue One 1.7 MP does not support set binning.')
        else:
            raise NotImplementedError(f'Set binning not implemented for camera {self.device_model_name()}')

    @synchronized("_mutex")
    @override
    def getBinning(self):
        if self.device_model_name() == 'C-BLUE ONE 1.7 MP':
            return 1
        else:
            raise NotImplementedError(f'Get binning not implemented for camera {self.device_model_name()}')

    @stop_start
    def set_conversion_efficiency(self, low_high_gain):
        ok = FliSdk_V2.FliCblueOne.SetConversionEfficiency(self._context, low_high_gain)
        self._logger.notice(f'Set conversion efficiency to: {low_high_gain} (0 = low, 1 = high)')

    @synchronized("_mutex")
    def get_conversion_efficiency(self):
        return FliSdk_V2.FliCblueOne.GetConversionEfficiency(self._context)[1]
    
    @stop_start
    def set_gain(self, gain_in_dB):
        ok = FliSdk_V2.FliCblueSfnc.SetGainSelector(self._context, CblueOne.GainSelector.AnalogAll)
        ok = FliSdk_V2.FliCblueSfnc.SetGain(self._context, gain_in_dB)
        self._logger.notice(f'Set analog gain to: {gain_in_dB} dB')

    @synchronized("_mutex")
    def get_gain(self):
        return FliSdk_V2.FliCblueSfnc.GetGain(self._context)[1]

    @override
    def registerCallback(self, callback):
        self._callbackList.append(callback)

    @synchronized("_mutex")
    @override
    def startAcquisition(self):
        pass

    @synchronized("_mutex")
    @override
    def stopAcquisition(self):
        pass

    @override
    def getFrameCounter(self):
        return FliSdk_V2.GetBufferFilling(self._context)

    @synchronized("_mutex")
    @override
    def getFrameRate(self):
        return FliSdk_V2.FliCblueSfnc.GetAcquisitionFrameRate(self._context)[1]
    
    @synchronized("_mutex")
    @override
    def getFrameRateMin(self):
        return FliSdk_V2.FliCblueSfnc.GetAcquisitionFrameRateMin(self._context)[1]
    
    @synchronized("_mutex")
    @override
    def getFrameRateMax(self):
        return FliSdk_V2.FliCblueSfnc.GetAcquisitionFrameRateMax(self._context)[1]

    @synchronized("_mutex")
    @override
    @stop_start
    def setFrameRate(self, frameRateInHz):
        framerate_max_hz = FliSdk_V2.FliCblueSfnc.GetAcquisitionFrameRateMax(self._context)[1]
        framerate_min_hz = FliSdk_V2.FliCblueSfnc.GetAcquisitionFrameRateMin(self._context)[1]
        if frameRateInHz < framerate_min_hz or frameRateInHz > framerate_max_hz:
            raise ValueError(f'Frame rate must be in the range {framerate_min_hz, framerate_max_hz} Hz') 
        
        ok = FliSdk_V2.FliCblueSfnc.SetAcquisitionFrameRate(self._context, frameRateInHz)
        self._logger.notice(f'Acquisition frame rate set to {frameRateInHz} Hz')

    @synchronized("_mutex")
    @override
    def deinitialize(self):
        FliSdk_V2.Stop(self._context)
        FliSdk_V2.Exit(self._context)

    @override
    def setParameter(self, name, value):
        if name == 'rows':
            self.set_rows(value)
        elif name == 'cols':
            self.set_cols(value)
        elif name == 'coolingSetPoint':
            self.set_device_cooling_setpoint(value)
        elif name == 'conversionEfficiency':
            self.set_conversion_efficiency(value)
        elif name == 'gain':
            self.set_gain(value)
        else:
            raise Exception('Parameter %s is not valid' % str(name))

    @override
    def getParameters(self):
        return {'rows': self.rows(),
                'cols': self.cols(),
                'coolingSetPoint': self.get_device_cooling_setpoint(),
                'conversionEfficiency': self.get_conversion_efficiency(),
                'gain': self.get_gain(),
                }