import abc
from six import with_metaclass
import numpy
from plico.utils.decorator import returns


__version__= "$Id: abstract_camera.py 268 2017-04-12 21:54:14Z lbusoni $"


class CameraException(Exception):
    '''Custom exception class in order to avoid
       exposing the Vimba namespace outside the context wrapper'''
    pass

class AbstractCamera(with_metaclass(abc.ABCMeta, object)):

    @abc.abstractmethod
    def name(self):
        assert False

    @abc.abstractmethod
    @returns(numpy.ndarray)
    def readFrame(self, timeoutMilliSec=2000):
        assert False

    @abc.abstractmethod
    def rows(self):
        assert False

    @abc.abstractmethod
    def cols(self):
        assert False

    @abc.abstractmethod
    def dtype(self):
        assert False

    @abc.abstractmethod
    def setExposureTime(self, exposureTimeInMilliSeconds):
        assert False

    @abc.abstractmethod
    def exposureTime(self):
        assert False

    @abc.abstractmethod
    def setBinning(self, binning):
        assert False

    @abc.abstractmethod
    def getBinning(self):
        assert False

    @abc.abstractmethod
    def registerCallback(self):
        assert False

    @abc.abstractmethod
    def startAcquisition(self):
        assert False

    @abc.abstractmethod
    def stopAcquisition(self):
        assert False

    @abc.abstractmethod
    def getFrameCounter(self):
        assert False

    @abc.abstractmethod
    def getFrameRate(self):
        assert False

    @abc.abstractmethod
    def setFrameRate(self, frameRateInHz):
        assert False

    @abc.abstractmethod
    def deinitialize(self):
        assert False

    @abc.abstractmethod
    def setParameter(self, name, value):
        assert False

    @abc.abstractmethod
    def getParameters(self):
        assert False



