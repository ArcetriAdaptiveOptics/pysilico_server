#!/usr/bin/env python
import unittest
import numpy as np
import logging
from test.test_helper import Poller, ExecutionProbe
from plico.utils.logger import Logger
from pysilico_server.devices.simulated_camera import \
    SimulatedPyramidWfsCamera

__version__ = "$Id: simulated_camera_test.py 271 2017-04-28 16:49:02Z lbusoni $"


class SimulatedPyramidWfsCameraTest(unittest.TestCase):

    def setUp(self):
        self._setUpLogging()
        self._camera = SimulatedPyramidWfsCamera()

    def tearDown(self):
        self._camera.stopAcquisition()
        self._camera.deinitialize()

    def _setUpLogging(self):
        FORMAT = '%(asctime)s %(levelname)s %(message)s'
        logging.basicConfig(level=logging.DEBUG, format=FORMAT)
        self._logger = Logger.of(self.__class__.__name__)

    def testReadFrameDimensionsAndType(self):
        self._camera.setBinning(1)
        f = self._camera.readFrame()
        self.assertEqual(f.shape, (self._camera.SENSOR_H,
                                   self._camera.SENSOR_W))
        self.assertEqual(f.dtype, self._camera.DTYPE)

    def testSetRadiusAndNoise(self):
        self._camera.setNoiseInCount(100.)
        self._camera.setPupilsRadiusInUnbinnedPixels(100)
        _ = self._camera.readFrame()

    def testFluxIsProportionalToExposureTime(self):
        self._camera.setNoiseInCount(0)
        self._camera.setExposureTime(1.0)
        ima1ms = self._camera.readFrame()
        self._camera.setExposureTime(2.5)
        ima2ms = self._camera.readFrame()
        self.assertAlmostEqual(2.5 * ima1ms.max(),
                               ima2ms.max(),
                               delta=3)

    def testFrameIsSaturatedIfFluxIsTooHigh(self):
        self._camera.setTotalFluxPerMilliSecond(1e9)
        frame = self._camera.readFrame()
        self.assertEqual(self._camera.MAX_VALUE,
                         frame.max())

    def testChangePupilsCenter(self):
        self._camera.setNoiseInCount(0)
        self._camera.setExposureTime(1.0)
        cp = 0.5 * np.array([self._camera.SENSOR_H,
                           self._camera.SENSOR_W])
        d = 0.1 * self._camera.SENSOR_H
        centers = np.zeros((4, 2))
        centers[0,:] = [cp[0] - d, cp[1] - d]
        centers[1,:] = [cp[0] + d, cp[1] - d]
        centers[2,:] = [cp[0] - d, cp[1] + d]
        centers[3,:] = [cp[0] + d, cp[1] + d]
        self._camera.setPupilsCenterInUnbinnedPixels(centers)
        self._camera.readFrame()

    def testWavefrontFromZernikeVector(self):
        tipPtV2Rms = 0.25
        ttCoeff = np.array([-1, 10]) * 1e-6
        self._camera.setNoiseInCount(0)
        self._camera.setScaleInMeterPerPixel(5e-6)
        self._camera.setSlopeSaturationInRadians(100e-3)
        self._camera.setWavefrontFromZernikeVector(ttCoeff)
        self._camera.setExposureTime(10)
        frame = self._camera.readFrame().astype(float)
        total = frame.sum()
        (sy, sx) = frame.shape
        dx = frame[:, -sx // 2:].sum() - frame[:, 0:sx // 2].sum()
        dy = frame[-sy // 2:,:].sum() - frame[0:sy // 2,:].sum()
        ttFromFlux = np.sin(np.pi / 2 * np.array([dx / total, dy / total])) * \
            self._camera.getSlopeSaturationInRadians() * \
            self._camera.getScaleInMeterPerPixel() * \
            self._camera.getPupilsRadiusInUnbinnedPixels() * 2 * \
            tipPtV2Rms
        self.assertTrue(np.allclose(ttCoeff, ttFromFlux, rtol=0.05),
                        "Wanted %s, got %s" % (ttCoeff, ttFromFlux))

    def _callback(self, frame):
        print ('callback %d' % frame.counter())
        self._lastFrameCounter = frame.counter()

    def testCallbackStartAndStop(self):
        print('testcallback')
        self._lastFrameCounter = 0
        self._camera.registerCallback(self._callback)

        def _frameCounterIncreased(self, originalFrameCounter):
            if self._lastFrameCounter <= originalFrameCounter:
                raise Exception("last %d - original %d" % (
                    self._lastFrameCounter, originalFrameCounter))

        self._camera.startAcquisition()
        Poller(2).check(ExecutionProbe(_frameCounterIncreased, '', self, 0))
        self._camera.stopAcquisition()
        currentFrameCnt = self._lastFrameCounter
        self.assertRaises(
            RuntimeError,
            Poller(2).check,
            ExecutionProbe(_frameCounterIncreased, '', self, currentFrameCnt)
        )


if __name__ == "__main__":
    unittest.main()
