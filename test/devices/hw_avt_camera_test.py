import unittest

try:
    import vimba
    from vimba import Vimba, VimbaFeatureError
except Exception:
    raise unittest.SkipTest(
        "vimba not installed. Skipping all tests in avt_camera_test.py")

from pysilico_server.devices.avtCamera import AvtCamera
from time import sleep
import functools


def withCamera():

    def wrapperFunc(f):

        @functools.wraps(f)
        def wrapper(self, *args, **kwds):
            with Vimba.get_instance():
                with self._vimbacamera:
                    return f(self, *args, **kwds)

        return wrapper

    return wrapperFunc


class HwAvtCameraTest(unittest.TestCase):

    def setUp(self):
        with Vimba.get_instance() as v:
            self._vimbacamera = v.get_all_cameras()[0]
        self._cam = AvtCamera(self._vimbacamera, 'camera_name')

    def test_exposure_time(self):
        self._cam.setExposureTime(100)
        exp_time = self._cam.exposureTime()
        self.assertAlmostEqual(100, exp_time)
        self._cam.setExposureTime(200)
        exp_time = self._cam.exposureTime()
        self.assertAlmostEqual(200, exp_time)

    def test_after_initialize(self):
        self.assertAlmostEqual(10000000,
                               self._cam.getStreamBytesPerSecond())
        self.assertAlmostEqual(1,
                               self._cam.getBinning())

    @withCamera()
    def test_framerate(self):
        wanted = 2
        self._cam.startAcquisition()
        sleep(3)
        self._cam.setFrameRate(wanted)
        got = self._cam.getFrameRate()
        self._cam.stopAcquisition()
        self.assertAlmostEqual(wanted, got)

    def test_print_info(self):
        print('model name %s' % self._cam.deviceModelName())
        print('id %s' % self._cam.deviceID())
        print('ip address %s' % self._cam.ipAddress())


class VimbaTest(unittest.TestCase):

    def test_list_features(self):
        with Vimba.get_instance() as v:
            vimbacamera = v.get_all_cameras()[0]
            with vimbacamera:
                for feature in vimbacamera.get_all_features():
                    self._print_feature(feature)

    def _print_feature(self, feature):
        try:
            value = feature.get()

        except (AttributeError, VimbaFeatureError):
            value = None

        print('/// Feature name   : {}'.format(feature.get_name()))
        print('/// Display name   : {}'.format(feature.get_display_name()))
        print('/// Tooltip        : {}'.format(feature.get_tooltip()))
        print('/// Description    : {}'.format(feature.get_description()))
        print('/// SFNC Namespace : {}'.format(feature.get_sfnc_namespace()))
        print('/// Unit           : {}'.format(feature.get_unit()))
        print('/// Value          : {}\n'.format(str(value)))


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
