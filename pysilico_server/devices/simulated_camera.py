#!/usr/bin/env python

import numpy as np
import time
from rebin import rebin
from plico.utils.zernike_generator import ZernikeGenerator
from plico.types.zernike_coefficients import ZernikeCoefficients
from pysilico_server.devices.base_simulated_camera import BaseSimulatedCamera
from plico.utils.decorator import logEnterAndExit

__version__ = "$Id: simulated_camera.py 293 2017-06-21 17:10:57Z lbusoni $"


class SimulatedPyramidWfsCamera(BaseSimulatedCamera):
    SENSOR_H = 1024
    SENSOR_W = 1360
    DTYPE = np.uint16
    MAX_VALUE = 4096

    def __init__(self, name='Simulated Pyramid Wfs Camera'):
        BaseSimulatedCamera.__init__(self, name)
        self._pupilRadius = None
        pupilsSeparation = 520
        opticalAxis = (self.SENSOR_H / 2, self.SENSOR_W / 2)
        self._pupilsCenter = self._computeCenters(pupilsSeparation,
                                                  opticalAxis)
        self._tipTiltCoefficients = np.zeros(2)
        self._wavefront = None
        self._zernikeGenerator = None

        self.setPupilsRadiusInUnbinnedPixels(80)
        self.setScaleInMeterPerPixel(
            10e-3 / (2 * self.getPupilsRadiusInUnbinnedPixels()))
        self.setSlopeSaturationInRadians(40e-3)

        self._logger.notice('Pupil centers %s' % (self._pupilsCenter))
        self._logger.notice('Pupil radius %s' % (self._pupilRadius))
        self.setFrameRate(3)

    def setPupilsRadiusInUnbinnedPixels(self, radius):
        self._pupilRadius = radius
        self._wavefront = np.zeros(
            (2 * self._pupilRadius, 2 * self._pupilRadius))
        self._zernikeGenerator = ZernikeGenerator(2 * self._pupilRadius)

    def getPupilsRadiusInUnbinnedPixels(self):
        return self._pupilRadius

    def setTilt(self, tipTiltCoefficients):
        self._tipTiltCoefficients = tipTiltCoefficients

    def setWavefront(self, wavefront):
        self._wavefront = wavefront

    def _computeWavefrontFromZernikeCoefficients(self, coeff, zg):
        wf = 0. * zg.getZernike(1)
        for y in coeff.zernikeIndexes():
            wf += coeff.getZ([y]) * zg.getZernike(y)
        return wf

    def setWavefrontFromZernikeVector(self, zernikeVector):
        wf = self._computeWavefrontFromZernikeCoefficients(
            ZernikeCoefficients.fromNumpyArray(np.array(zernikeVector)),
            self._zernikeGenerator)
        self.setWavefront(wf)

    def _computeCenters(self, pupilsSeparation, opticalAxis):
        pupDist = int(0.5 * pupilsSeparation)
        center = opticalAxis
        res = np.zeros((4, 2))
        res[0, :] = [center[0] + pupDist, center[1] - pupDist]
        res[1, :] = [center[0] + pupDist, center[1] + pupDist]
        res[2, :] = [center[0] - pupDist, center[1] - pupDist]
        res[3, :] = [center[0] - pupDist, center[1] + pupDist]
        return res

    def setPupilsCenterInUnbinnedPixels(self, centers):
        assert centers.shape == (4, 2)
        self._pupilsCenter = centers

    def getPupilsCenterInUnbinnedPixels(self):
        return self._pupilsCenter

    def _computeFluxesForTilt(self):
        z2 = self._tipTiltCoefficients[0]
        z3 = self._tipTiltCoefficients[1]
        tot = 4.0
        tl = 0.25 * (z3 - z2 + 1) * tot
        tr = 0.25 * (z3 + z2 + 1) * tot
        bl = 0.25 * (-z3 - z2 + 1) * tot
        br = 0.25 * (-z3 + z2 + 1) * tot
        self._logger.debug(
            "tl,tr,bl,br %g,%g,%g,%g - z2,z3: %g,%g" %
            (tl, tr, bl, br, (tr + br - tl - bl) / tot,
             (tl + tr - bl - br) / tot))
        return tl, tr, bl, br

    def _pupilImagesFromWavefront(self, wavefront):
        Amat = np.array([[1., 0, 1, 0],
                         [0., 1, 0, 1],
                         [0., 0, 1, 1],
                         [1., 1, 0, 0]])

        (dyMap, dxMap) = np.gradient(wavefront / self._scaleInMeterPerPixel)
        dxMapClipped = dxMap.clip(min=-self._slopeSaturationInRad,
                                  max=self._slopeSaturationInRad)
        dyMapClipped = dyMap.clip(min=-self._slopeSaturationInRad,
                                  max=self._slopeSaturationInRad)
        dx = 2. / np.pi * np.arcsin(dxMapClipped / self._slopeSaturationInRad)
        dy = 2. / np.pi * np.arcsin(dyMapClipped / self._slopeSaturationInRad)
        (sz0, sz1) = dxMap.shape
        totalIntensity = 1. * sz0 * sz1
        B = totalIntensity / (sz0 * sz1) / 2 * np.array(
            [1 - dx, 1 + dx, 1 - dy, 1 + dy])

        res = np.linalg.lstsq(Amat, B.reshape((4, sz0 * sz1)), rcond=-1)
        pupils = res[0].reshape((4, sz0, sz1))

        if isinstance(wavefront, np.ma.MaskedArray):
            for i in range(4):
                pupils[i][wavefront.mask] = 0

        return pupils

    @logEnterAndExit('Enter _computeFrameFromWavefront',
                     'Exit _computeFrameFromWavefront',
                     level='debug')
    def _computeFrameFromWavefront(self):
        radius = self._pupilRadius
        cc = self._pupilsCenter
        maxNoiseInCount = self._noiseInCount

        pupils = self._pupilImagesFromWavefront(self._wavefront)
        pixels = np.zeros((self.SENSOR_H, self.SENSOR_W),
                          dtype=float)

        pixels[int(cc[0, 0] - radius): int(cc[0, 0] + radius),
               int(cc[0, 1] - radius): int(cc[0, 1] + radius)] = pupils[0]
        pixels[int(cc[1, 0] - radius): int(cc[1, 0] + radius),
               int(cc[1, 1] - radius): int(cc[1, 1] + radius)] = pupils[1]
        pixels[int(cc[2, 0] - radius): int(cc[2, 0] + radius),
               int(cc[2, 1] - radius): int(cc[2, 1] + radius)] = pupils[2]
        pixels[int(cc[3, 0] - radius): int(cc[3, 0] + radius),
               int(cc[3, 1] - radius): int(cc[3, 1] + radius)] = pupils[3]

        normalize = self._totalFluxPerMilliSecond * \
            self.exposureTime() / pixels.sum()
        pixels *= normalize

        if maxNoiseInCount > 0:
            pixels += np.random.normal(
                3 * maxNoiseInCount,
                maxNoiseInCount,
                size=(self.SENSOR_H, self.SENSOR_W))

        if self._binning != 1:
            pixels = rebin(pixels, self._binning) * self._binning ** 2
        pixels = pixels.clip(min=0, max=self.MAX_VALUE)

        time.sleep(1. / self.getFrameRate())
        return pixels.astype(self.DTYPE)

    def setSlopeSaturationInRadians(self, slopeSaturationInRadians):
        self._slopeSaturationInRad = slopeSaturationInRadians

    def getSlopeSaturationInRadians(self):
        return self._slopeSaturationInRad

    def setScaleInMeterPerPixel(self, scaleInMeterPerPixel):
        self._scaleInMeterPerPixel = scaleInMeterPerPixel

    def getScaleInMeterPerPixel(self):
        return self._scaleInMeterPerPixel
