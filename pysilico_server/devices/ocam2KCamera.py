
import re
import time
import numpy as np
import threading

import FliSdk_V2

from plico.utils.decorator import logEnterAndExit, \
            synchronized, override
from pysilico_server.devices.abstract_camera import AbstractCamera
from plico.utils.logger import Logger
from pysilico.types.camera_frame import CameraFrame

# Example of bash script to set environment variables
# and also the current directory before starting
'''
BASEDIR=/opt/FirstLightImaging

export PYTHONPATH=$BASEDIR/FliSdk/Python/lib
export LD_LIBRARY_PATH=/home/labot/anaconda3/envs/p37/lib:$BASEDIR/FirstLightVision/lib

(cd $BASEDIR/FirstLightVision && pysilico_start)
'''



class Ocam2KLowLevel():

    def __init__(self, cameraIndex=0, verbose=True, binning=1, synchro=False, start=True, logFunc=print):

        def myLogFunc(*args):
            logFunc(' '.join(map(str, args)))

        if not binning in [1,2]:
            raise Exception('Binning must be either 1 or 2')

        self.logFunc = myLogFunc
        self.started = False
        context = FliSdk_V2.Init()
        self.verbose = verbose
        self.context = context

        if verbose: myLogFunc("Detection of grabbers...")
        listOfGrabbers = FliSdk_V2.DetectGrabbers(context)

        if len(listOfGrabbers) == 0:
            raise Exception("No grabber detected, exit.")

        if verbose:
            myLogFunc("Done.")
            myLogFunc("List of detected grabber(s):")
            for s in listOfGrabbers:
                myLogFunc("- " + s)

        if verbose: myLogFunc("Detection of cameras...")
        listOfCameras = FliSdk_V2.DetectCameras(context)

        if len(listOfCameras) == 0:
            raise Exception("No camera detected, exit.")

        if verbose:
            myLogFunc("Done.")
            myLogFunc("List of detected camera(s):")
            for i,s in enumerate(listOfCameras):
                myLogFunc("- " + str(i) + " -> " + s)

        if cameraIndex is None:
            cameraIndex = int(input("Which camera to use? (0, 1, ...) "))

        if verbose: myLogFunc("Setting camera: " + listOfCameras[cameraIndex])
        ok = FliSdk_V2.SetCamera(context, listOfCameras[cameraIndex])

        if not ok:
            raise Exception("Error while setting camera.")

        result = FliSdk_V2.SetMode(context, FliSdk_V2.Mode.Full)
        if verbose: myLogFunc("Setting mode full:", result)

        result = FliSdk_V2.FliOcam2K.SetWorkMode(context)
        if verbose: myLogFunc('SetWorkMode:', result)

        isOcam2k = FliSdk_V2.IsOcam2k(context)
        if verbose: myLogFunc('IsOcam2K:', isOcam2k)

        result = FliSdk_V2.GetCameraModel(context)
        if verbose: myLogFunc('GetCameraModel ', result)

        result = FliSdk_V2.GetCurrentCameraName(context)
        if verbose: myLogFunc('GetCurrentCameraName ', result)

        ok = FliSdk_V2.Update(context)
        if not ok:
             raise Exception('Error updating SDK with final parameters')

        self.setBinning(binning)
        self.protectionReset()
        self.setSyncro(synchro)
        self.setEMGain(1)
        self.setTemperatureSetPoint(20)

        cmd = 'temp on'
        res, response = FliSdk_V2.FliSerialCamera.SendCommand(context, cmd)
        if verbose: myLogFunc(cmd+':', res, response)

        width, height = FliSdk_V2.GetCurrentImageDimension(context)
        if verbose: myLogFunc('width, height:', width, height)

        self._width = width
        self._height = height

        result = FliSdk_V2.EnableUnsignedPixel(context, True)
        if verbose: myLogFunc('EnableUnsignedPixel:', result)

        result = FliSdk_V2.SetBufferSize(context, 1000)
        if verbose: myLogFunc('SetBufferSize:', result)

        result = FliSdk_V2.EnableRingBuffer(context, True)
        if verbose: myLogFunc('EnableRingBuffer:', result)

        result = FliSdk_V2.GetImagesCapacity(context)
        if verbose: myLogFunc('GetImagesCapacity:', result)

        result = FliSdk_V2.GetBufferSize(context)
        if verbose: myLogFunc('GetBufferSize:', result)

        result = FliSdk_V2.GetImagesCapacity(context)
        if verbose: myLogFunc('GetImagesCapacity:', result)

        result = FliSdk_V2.ResetBuffer(context)
        if verbose: myLogFunc('ResetBuffer:', result)

        ok = FliSdk_V2.Update(context)

        self.stop(force=True)
        if start:
            self.start()

        self._lastIndex = None

    def getWidth(self):
        return self._width

    def getHeight(self):
        return self._height

    def setBinning(self, binning):

        if binning == 1:
            result = FliSdk_V2.FliOcam2K.SetStandardMode(self.context)
            if self.verbose: self.logFunc('SetStandardMode:', result)
            result = FliSdk_V2.FliSerialCamera.SetFps(self.context, float(2000))
            if self.verbose: self.logFunc('SetFps(2000):', result)

        elif binning == 2:
            result = FliSdk_V2.FliOcam2K.SetBinning2x2Mode(self.context)
            if self.verbose: self.logFunc('SetBinning2x2Mode:', result)
            result = FliSdk_V2.FliSerialCamera.SetFps(self.context, float(3600))
            if self.verbose: self.logFunc('SetFps(3600):', result)
        
        else:
            raise Exception('Binning %s not supported' % str(binning))

    def addCallback(self, func, fps, beforeCopy=False, userdata=None):
        '''Adds a callback for new images that will be called
        at no more than *fps* Hz. If *beforeCopy* is True, the image
        will be in the frame grabber memory and be available
        for a short time only, but this mode has a very low latency.
        *userdata* will be passed as-is to the callback function
        as the second argument.'''
        FliSdk_V2.AddCallBackNewImage(self.context, func, fps, beforeCopy, userdata)

    def start(self):
        if not self.started:
            result = FliSdk_V2.Start(self.context)
            if self.verbose: self.logFunc('Start:', result)
            self.started = True

    def stop(self, force=False):
        if self.started or force:
            result = FliSdk_V2.Stop(self.context)
            if self.verbose: self.logFunc('Stop:', result)
            self.started = False

    def setFps(self, fps):
        if fps<10 or fps>2000:
            raise Exception('FPS must be between 10 and 2000')
        result = FliSdk_V2.FliSerialCamera.SetFps(self.context, float(fps))
        if self.verbose: self.logFunc('SetFps:', result)

    def getFps(self):
        result, fps = FliSdk_V2.FliSerialCamera.GetFps(self.context)
        if self.verbose: self.logFunc('GetFps:', result)
        return fps

    def setEMGain(self, emgain):
        if emgain<1 or emgain>400:
            raise Exception('EM gain must be between 1 and 400 included')
        cmd = 'gain %d' % emgain
        res, response = FliSdk_V2.FliSerialCamera.SendCommand(self.context, cmd)
        if self.verbose: self.logFunc(cmd+':', res, response)

    def getEMGain(self):
        cmd = 'gain'
        res, response = FliSdk_V2.FliSerialCamera.SendCommand(self.context, cmd)
        if self.verbose: self.logFunc(cmd+':', res, response)
        gain = re.findall(r'\d+', response)[0]
        return int(gain)

    def protectionReset(self):
        result = FliSdk_V2.FliOcam2K.ProtectionReset(self.context)
        if self.verbose: self.logFunc('ProtectionReset:', result)

    def setSyncro(self, ttsync):
        cmd = 'synchro ' + ('on' if ttsync else 'off')
        res, response = FliSdk_V2.FliSerialCamera.SendCommand(self.context, cmd)
        self.logFunc(cmd+':', res, response)
        self._syncro = ttsync

    def getSyncro(self):
        return self._syncro

    def getCurrentIndex(self):
        return FliSdk_V2.GetBufferFilling(self.context)

    def getFrame(self, index=-1, next=False, timeout=1):

        if next is True:
             start = time.time()
             index = self.getCurrentIndex()
             while index == self._lastIndex:
                  if time.time()-start > timeout:
                      raise TimeoutError('Timeout waiting for Ocam2K frames')
                  index = self.getCurrentIndex()
             self._lastIndex = index
 
        return FliSdk_V2.GetRawImageAsNumpyArray(self.context, index)

    def saveFrames(self, nFrames, filename=None):

        result = FliSdk_V2.ResetBuffer(self.context)
        if self.verbose: self.logFunc('ResetBuffer:', result)

        self.start()

        result = FliSdk_V2.EnableGrabN(self.context, nFrames)
        if self.verbose: self.logFunc('EnableGrabN:', result)

        while not FliSdk_V2.IsGrabNFinished(self.context):
            result = FliSdk_V2.GetBufferFilling(self.context)
            if self.verbose: self.logFunc('GetBufferFilling:', result)
            time.sleep(0.1)

        result = FliSdk_V2.DisableGrabN(self.context)
        if self.verbose: self.logFunc('DisableGrabN:', result)

        if filename:
            if self.verbose: self.logFunc('Saving to %s...', filename)
            result = FliSdk_V2.SaveBuffer(self.context, filename, 0, nFrames)
            if self.verbose: self.logFunc('SaveBuffer:', result)

    def getTemperature(self):
        result, *allTemp = FliSdk_V2.FliOcam2K.GetAllTemp(self.context)
        if self.verbose: self.logFunc('GetAllTemp:', result)
        return allTemp[0]

    def getTemperatureSetPoint(self):
        result, *allTemp = FliSdk_V2.FliOcam2K.GetAllTemp(self.context)
        if self.verbose: self.logFunc('GetAllTemp:', result)
        return allTemp[7]

    def setTemperatureSetPoint(self, setpoint):
        cmd = 'temp %d' % int(setpoint)
        res, response = FliSdk_V2.FliSerialCamera.SendCommand(self.context, cmd)
        if self.verbose: self.logFunc(cmd+':', res, response)

    def __del__(self):
        self.stop()
        FliSdk_V2.Exit(self.context)


class RepeatTimer(threading.Timer):
    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)

class Ocam2KCamera(AbstractCamera):

    def __init__(self, name):
        self._logger = Logger.of('Ocam2KCamera')
        self._camera = Ocam2KLowLevel(binning=1, logFunc=self._logger.notice)
        self._name = name
        self._binning = 1
        self._ncols = self._camera.getWidth()
        self._nrows = self._camera.getHeight()
        self._maxClientFps = 100
        self._mutex = threading.RLock()
        self._timer = RepeatTimer(0.005, self.timer)
        self._callbackList = []
        self._timer.start()

       # FliSdk callbacks seem not to work
       # self._camera.addCallback(self._newFrameCallback, self._maxClientFps, beforeCopy=False, userdata=None)

 #   def _newFrameCallback(self, frame, userdata):
  #      print(frame)
  #      print(userdata)
  #      for callback in self._callbackList:
   #         callback(frame)

    def timer(self):
        frame = self.readFrame()
        cameraFrame = CameraFrame(frame, counter=self.getFrameCounter())
        for callback in self._callbackList:
            callback(cameraFrame)

    @override
    def startAcquisition(self):
        pass

    @override
    def stopAcquisition(self):
        pass

    @override
    def getFrameCounter(self):
        return self._camera.getCurrentIndex()

    @override
    def readFrame(self, timeoutMilliSec=2000):
        return self._camera.getFrame(index=-1, next=True, timeout=timeoutMilliSec/1000)

    @override
    @synchronized("_mutex")
    def setBinning(self, binning):
        self._camera.setBinning(binning)
        self._binning = binning

    @override
    def getBinning(self):
        return self._binning

    @override
    def name(self):
        return self._name

    @override
    def rows(self):
        return self._nrows/self._binning

    @override
    def cols(self):
        return self._ncols/self._binning

    @override
    def dtype(self):
        return np.uint16

    @override
    @synchronized("_mutex")
    def setExposureTime(self, exposureTimeInMilliSeconds):
        self._camera.setFps(1000/exposureTimeInMilliSeconds)

    @override
    @synchronized("_mutex")
    def exposureTime(self):
        return self._camera.getFps()

    @override
    @synchronized("_mutex")
    def setFrameRate(self, frameRate):
        self._camera.setFps(frameRate)

    @synchronized("_mutex")
    def getFrameRate(self):
        return self._camera.getFps()

    @override
    def registerCallback(self, callback):
        self._callbackList.append(callback)

    @override
    def deinitialize(self):
        pass

    @override
    def setParameter(self, name, value):
        if name == 'EMGain':
            self._camera.setEMGain(value)
        elif name == 'temperatureSetPoint':
            self._camera.setTemperatureSetPoint(value)
        elif name == 'TTLSync':
            self._camera.setSyncro(value)
        elif name == 'protectionReset':
            self._camera.protectionReset()
        else:
            raise Exception('Parameter %s is not valid' % str(name))

    @override
    def getParameters(self):
        return {'EMGain': self._camera.getEMGain(),
                'temperatureSetPoint': self._camera.getTemperatureSetPoint(),
                'chipTemperature': self._camera.getTemperature(),
                'TTLSync': self._camera.getSyncro(),
                'protection': False,
                }




