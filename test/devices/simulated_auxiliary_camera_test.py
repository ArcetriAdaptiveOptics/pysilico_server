#!/usr/bin/env python
import unittest
import numpy as np
import logging
from pysilico_server.devices.simulated_auxiliary_camera import \
    SimulatedAuxiliaryCamera
from plico.utils.logger import Logger


class SimulatedAuxiliaryCameraTest(unittest.TestCase):

    def setUp(self):
        self._setUpLogging()
        self._camera = SimulatedAuxiliaryCamera()

    def tearDown(self):
        self._camera.raiseExceptionOnDeinitialize(False)
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

    def testSetNoise(self):
        self._camera.setNoiseInCount(100.)
        f = self._camera.readFrame()
        self.assertAlmostEqual(100, np.std(f[0:100, 0:100]), delta=3)

    def testFluxIsProportionalToExposureTime(self):
        self._camera.setNoiseInCount(0)
        self._camera.setExposureTime(0.1)
        ima1ms = self._camera.readFrame()
        self._camera.setExposureTime(0.25)
        ima2ms = self._camera.readFrame()
        self.assertAlmostEqual(2.5 * ima1ms.max(),
                               ima2ms.max(),
                               delta=3)

    def testFrameIsSaturatedIfFluxIsTooHigh(self):
        self._camera.setTotalFluxPerMilliSecond(1e9)
        frame = self._camera.readFrame()
        self.assertEqual(self._camera.MAX_VALUE,
                         frame.max())


if __name__ == "__main__":
    unittest.main()
