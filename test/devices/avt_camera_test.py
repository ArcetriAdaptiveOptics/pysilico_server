import unittest
import numpy as np
from pysilico_server.devices.avtCamera import Vimba, AvtCamera


__version__ = "$Id: avt_camera_test.py 311 2017-10-10 16:39:33Z pygo $"


class MyVimbaStructureFrame():

    def __init__(self):
        self.receiveStatus= 0


class MyVimbaFrame(object):
    def __init__(self, h, w, dtype):
        self._h= h
        self._w= w
        self._dtype= dtype
        self._frame= MyVimbaStructureFrame()

    def announceFrame(self):
        pass

    def queueFrameCapture(self):
        self._frame.receiveStatus= 1

    def waitFrameCapture(self, timeout=2000):
        self._frame.receiveStatus= 0
        return 0

    def getBufferByteData(self):
        return memoryview(np.ones((self._h, self._w), dtype=self._dtype))

    @property
    def height(self):
        return self._h

    @property
    def width(self):
        return self._w


class MyVimbaCamera(object):
    IP_ADDRESS= '193.206.155.159'
    SENSOR_SIZE_H= 1024
    SENSOR_SIZE_W= 768


    def __init__(self):
        self.enableBinning()
        self.disableDecimation()

        self.PixelFormat= 'Mono12'
        self.DeviceModelName= 'bar'
        self.DeviceID= '02-2060C-06184'
        self.GevCurrentIPAddress= int(2677788353)
        self.GevTimestampTickFrequency=int(10000)
        self.SensorHeight= self.SENSOR_SIZE_H
        self.SensorWidth= self.SENSOR_SIZE_W
        self.SensorBits= 12
        self.ExposureTimeAbs= 10000.


    def __getattr__(self, attr):
        try:
            return self.__dict__[attr]
        except KeyError:
            raise AttributeError


    def __setattr__(self, name, value):
        if name[0] != '_':
            self._checkDecimationEnabled(name, value)
            self._checkBinningEnabled(name, value)
        self.__dict__[name]= value


    def _checkDecimationEnabled(self, name, value):
        if name in [Vimba.DECIMATION_HORIZONTAL,
                    Vimba.DECIMATION_VERTICAL]:
            if self._decimationEnabled is False:
                raise KeyError(name)


    def _checkBinningEnabled(self, name, value):
        if name in [Vimba.BINNING_HORIZONTAL,
                    Vimba.BINNING_VERTICAL]:
            if self._binningEnabled is False:
                raise KeyError(name)


    def getFeatureNames(self):
        dicto= self.__dict__
        print(dicto)
        return dicto


    def openCamera(self):
        pass


    def startCapture(self):
        pass


    def endCapture(self):
        pass


    def flushCaptureQueue(self):
        pass


    def runFeatureCommand(self, command):
        pass


    def getFrame(self):
        return MyVimbaFrame(self.SensorHeight, self.SensorWidth, np.uint16)


    def revokeAllFrames(self):
        pass


    def enableBinning(self):
        self._binningEnabled= True
        self.BinningHorizontal= 1
        self.BinningVertical= 1


    def disableBinning(self):
        self._binningEnabled= False
        self.__dict__.pop(Vimba.BINNING_HORIZONTAL, None)
        self.__dict__.pop(Vimba.BINNING_VERTICAL, None)


    def enableDecimation(self):
        self._decimationEnabled= True
        self.DecimationHorizontal= 1
        self.DecimationVertical= 1


    def disableDecimation(self):
        self._decimationEnabled= False
        self.__dict__.pop(Vimba.DECIMATION_HORIZONTAL, None)
        self.__dict__.pop(Vimba.DECIMATION_VERTICAL, None)


class TestAvtCamera(unittest.TestCase):


    def setUp(self):
        self.vimbacamera= MyVimbaCamera()
        self.avt= AvtCamera(self.vimbacamera, 'foo')


    def test_creation(self):
        self.assertEqual(MyVimbaCamera.IP_ADDRESS, self.avt.ipAddress())


    def testSetBinningUsingDecimation(self):
        self.vimbacamera.disableBinning()
        self.vimbacamera.enableDecimation()
        self.avt.setBinning(1)
        self.assertEqual(1, self.vimbacamera.DecimationHorizontal)
        self.assertEqual(1, self.vimbacamera.DecimationVertical)
        self.assertEqual(self.vimbacamera.SENSOR_SIZE_H, self.avt.rows())
        self.assertEqual(self.vimbacamera.SENSOR_SIZE_W, self.avt.cols())
        self.avt.setBinning(4)
        self.assertEqual(4, self.vimbacamera.DecimationHorizontal)
        self.assertEqual(4, self.vimbacamera.DecimationVertical)
        self.assertEqual(self.vimbacamera.SENSOR_SIZE_H/ 4, self.avt.rows())
        self.assertEqual(self.vimbacamera.SENSOR_SIZE_W/ 4, self.avt.cols())
        self.assertEqual(4, self.avt.getBinning())



    def testSetBinningWithoutDecimation(self):
        self.vimbacamera.enableBinning()
        self.vimbacamera.disableDecimation()
        self.avt.setBinning(1)
        self.assertEqual(1, self.vimbacamera.BinningHorizontal)
        self.assertEqual(1, self.vimbacamera.BinningVertical)
        self.assertEqual(self.vimbacamera.SENSOR_SIZE_H, self.avt.rows())
        self.assertEqual(self.vimbacamera.SENSOR_SIZE_W, self.avt.cols())
        self.avt.setBinning(4)
        self.assertEqual(4, self.vimbacamera.BinningHorizontal)
        self.assertEqual(4, self.vimbacamera.BinningVertical)
        self.assertEqual(self.vimbacamera.SENSOR_SIZE_H/ 4, self.avt.rows())
        self.assertEqual(self.vimbacamera.SENSOR_SIZE_W/ 4, self.avt.cols())
        self.assertEqual(4, self.avt.getBinning())


    def testSetBinningWithoutDecimationNorBinningRaisesException(self):
        self.vimbacamera.disableBinning()
        self.vimbacamera.disableDecimation()
        self.assertRaises(Exception, self.avt.setBinning, 1)




if __name__ == "__main__":
    unittest.main()
