#!/usr/bin/env python

import numpy as np
import time
from pysilico_server.devices.base_simulated_camera import BaseSimulatedCamera


class SimulatedAuxiliaryCamera(BaseSimulatedCamera):

    def __init__(self, name='SimulatedAuxiliaryCamera'):
        BaseSimulatedCamera.__init__(self, name)
        self._totalFluxPerMilliSecond = 1e5
        self.setFrameRate(3)

    def _makeLetterF(self, h, w):
        pixels = np.zeros((h, w), dtype=float)
        b = min(h, w) // 7

        pixels[b:6 * b, int(w / 2 - 1.5 * b):int(w / 2 - 0.5 * b)] = 1
        pixels[b:2 * b, int(w / 2 - 1.5 * b):int(w / 2 + 2.0 * b)] = 1
        pixels[3 * b:4 * b, int(w / 2 - 1.5 * b):int(w / 2 + 2.0 * b)] = 1
        return pixels

    def _makeCentralSpot(self, h, w):
        pixels = np.zeros((h, w), dtype=np.float)
        pixels[int(h / 2): int(h / 2 + 1),
               int(w / 2): int(w / 2 + 1)] = 1.0
        return pixels

    def _computeFrameFromWavefront(self):
        h, w = (self.rows(), self.cols())

        pixels = self._makeLetterF(h, w)

        normalize = self._totalFluxPerMilliSecond * \
            self.exposureTime() / pixels.sum()
        pixels *= normalize

        if self._noiseInCount > 0:
            pixels += np.random.normal(
                3 * self._noiseInCount,
                self._noiseInCount,
                size=(h, w))

        # if self.getBinning() != 1:
        #    pixels= rebin(pixels, self.getBinning()) * \
        #        self.getBinning()**2
        pixels = pixels.clip(min=0, max=self.MAX_VALUE)

        self._counter += 1
        time.sleep(1. / self.getFrameRate())
        return pixels.astype(self.DTYPE)
