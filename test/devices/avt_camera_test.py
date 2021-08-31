import unittest

try:
    import vimba
except Exception:
    raise unittest.SkipTest(
        "vimba not installed. Skipping all tests in avt_camera_test.py")

import numpy as np
from pysilico_server.devices.avtCamera import Vimba, AvtCamera
from vimba.frame import PixelFormat


class MyVimbaStructureFrame():

    def __init__(self):
        self.receiveStatus = 0


class MyVimbaFrame(object):

    def __init__(self, h, w, dtype):
        self._h = h
        self._w = w
        self._dtype = dtype
        self._frame = MyVimbaStructureFrame()

    def announceFrame(self):
        pass

    def queueFrameCapture(self):
        self._frame.receiveStatus = 1

    def waitFrameCapture(self, timeout=2000):
        self._frame.receiveStatus = 0
        return 0

    def getBufferByteData(self):
        return memoryview(np.ones((self._h, self._w), dtype=self._dtype))

    @property
    def height(self):
        return self._h

    @property
    def width(self):
        return self._w


class MyFeature():

    def __init__(self, name, value):
        self._name = name
        self._value = value

    def get_name(self):
        return self._name

    def get(self):
        return self._value

    def set(self, value):
        self._value = value


class MyVimbaCamera(object):
    IP_ADDRESS = '193.206.155.159'
    SENSOR_SIZE_H = 1024
    SENSOR_SIZE_W = 768

    def __init__(self):

        self.set_pixel_format(PixelFormat.Mono12)
        self._deviceModelName = 'bar'
        self._deviceID = '02-2060C-06184'
        self._feat_dict = {}
        feats = (
            MyFeature('GevCurrentIPAddress', int(2677788353)),
            MyFeature('GevTimestampTickFrequency', int(10000)),
            MyFeature('SensorHeight', self.SENSOR_SIZE_H),
            MyFeature('SensorWidth', self.SENSOR_SIZE_W),
            MyFeature('SensorBits', 12),
            MyFeature('ExposureTimeAbs', 10000.),
            MyFeature('StreamBytesPerSecond', 1000000),
            MyFeature('OffsetX', 0),
            MyFeature('OffsetY', 0),
            MyFeature('Height', 100),
            MyFeature('Width', 200),
            MyFeature('GVSPPacketSize', 1500),
        )
        for f in feats:
            self._feat_dict[f.get_name()] = f

        self.enableBinning()
        self.disableDecimation()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def __getattr__(self, attr):
        if attr[0] != '_':
            try:
                return self._feat_dict[attr]
            except KeyError:
                raise AttributeError
        else:
            try:
                return self.__dict__[attr]
            except KeyError:
                raise AttributeError(attr)

    def __setattr__(self, name, value):
        if name[0] != '_':
            self._checkDecimationEnabled(name, value)
            self._checkBinningEnabled(name, value)
            self._feat_dict[name] = MyFeature(name, value)
        else:
            self.__dict__[name] = value

    def _checkDecimationEnabled(self, name, value):
        if name in [AvtCamera.VIMBA_DECIMATION_HORIZONTAL,
                    AvtCamera.VIMBA_DECIMATION_VERTICAL]:
            if self._decimationEnabled is False:
                raise KeyError(name)

    def _checkBinningEnabled(self, name, value):
        if name in [AvtCamera.VIMBA_BINNING_HORIZONTAL,
                    AvtCamera.VIMBA_BINNING_VERTICAL]:
            if self._binningEnabled is False:
                raise KeyError(name)

    def get_all_features(self):
        dicto = self._feat_dict.values()
        return dicto

    # def openCamera(self):
    #     pass
    #
    # def startCapture(self):
    #     pass
    #
    # def endCapture(self):
    #     pass
    #
    # def flushCaptureQueue(self):
    #     pass
    #
    # def runFeatureCommand(self, command):
    #     pass
    #
    # def getFrame(self):
    #     return MyVimbaFrame(self.SensorHeight, self.SensorWidth, np.uint16)
    #
    # def revokeAllFrames(self):
    #     pass

    def enableBinning(self):
        self._binningEnabled = True
        self.BinningHorizontal = 1
        self.BinningVertical = 1

    def disableBinning(self):
        self._binningEnabled = False
        self._feat_dict.pop(AvtCamera.VIMBA_BINNING_HORIZONTAL, None)
        self._feat_dict.pop(AvtCamera.VIMBA_BINNING_VERTICAL, None)

    def enableDecimation(self):
        self._decimationEnabled = True
        self.DecimationHorizontal = 1
        self.DecimationVertical = 1

    def disableDecimation(self):
        self._decimationEnabled = False
        self._feat_dict.pop(AvtCamera.VIMBA_DECIMATION_HORIZONTAL, None)
        self._feat_dict.pop(AvtCamera.VIMBA_DECIMATION_VERTICAL, None)

    def set_pixel_format(self, format):
        self._pixel_format = format

    def get_pixel_format(self):
        return self._pixel_format

    def get_id(self):
        return self._deviceID

    def get_model(self):
        return self._deviceModelName


class TestAvtCamera(unittest.TestCase):

    def setUp(self):
        self.vimbacamera = MyVimbaCamera()
        self.avt = AvtCamera(self.vimbacamera, 'foo')

    def test_creation(self):
        self.assertEqual(MyVimbaCamera.IP_ADDRESS, self.avt.ipAddress())

    def testSetBinningUsingDecimation(self):
        self.vimbacamera.disableBinning()
        self.vimbacamera.enableDecimation()
        self.avt.setBinning(1)
        self.assertEqual(1, self.vimbacamera.DecimationHorizontal.get())
        self.assertEqual(1, self.vimbacamera.DecimationVertical.get())
        self.assertEqual(self.vimbacamera.SENSOR_SIZE_H, self.avt.rows())
        self.assertEqual(self.vimbacamera.SENSOR_SIZE_W, self.avt.cols())
        self.avt.setBinning(4)
        self.assertEqual(4, self.vimbacamera.DecimationHorizontal.get())
        self.assertEqual(4, self.vimbacamera.DecimationVertical.get())
        self.assertEqual(self.vimbacamera.SENSOR_SIZE_H / 4, self.avt.rows())
        self.assertEqual(self.vimbacamera.SENSOR_SIZE_W / 4, self.avt.cols())
        self.assertEqual(4, self.avt.getBinning())

    def testSetBinningWithoutDecimation(self):
        self.vimbacamera.enableBinning()
        self.vimbacamera.disableDecimation()
        self.avt.setBinning(1)
        self.assertEqual(1, self.vimbacamera.BinningHorizontal.get())
        self.assertEqual(1, self.vimbacamera.BinningVertical.get())
        self.assertEqual(self.vimbacamera.SENSOR_SIZE_H, self.avt.rows())
        self.assertEqual(self.vimbacamera.SENSOR_SIZE_W, self.avt.cols())
        self.avt.setBinning(4)
        self.assertEqual(4, self.vimbacamera.BinningHorizontal.get())
        self.assertEqual(4, self.vimbacamera.BinningVertical.get())
        self.assertEqual(self.vimbacamera.SENSOR_SIZE_H / 4, self.avt.rows())
        self.assertEqual(self.vimbacamera.SENSOR_SIZE_W / 4, self.avt.cols())
        self.assertEqual(4, self.avt.getBinning())

    def testSetBinningWithoutDecimationNorBinningRaisesException(self):
        self.vimbacamera.disableBinning()
        self.vimbacamera.disableDecimation()
        self.assertRaises(Exception, self.avt.setBinning, 1)


if __name__ == "__main__":
    unittest.main()
