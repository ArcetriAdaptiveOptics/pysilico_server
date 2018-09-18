#!/usr/bin/env python
import unittest
from pysilico_server.devices.simulated_auxiliary_camera import \
    SimulatedAuxiliaryCamera
from pysilico_server.camera_controller.camera_controller import \
    CameraController

__version__ = "$Id: camera_controller_test.py 293 2017-06-21 17:10:57Z lbusoni $"


class MyReplySocket():
    pass


class MyPublisherSocket():
    pass


class MyRpcHandler():

    def __init__(self):
        self._publish= {}


    def handleRequest(self, obj, socket, multi):
        pass


    def publishPickable(self, socket, anObject):
        self._publish[socket]= anObject


    def getLastPublished(self, socket):
        return self._publish[socket]


    def sendCameraFrame(self, socket, frame):
        self.publishPickable(socket, frame)


class CameraControllerTest(unittest.TestCase):

    def setUp(self):
        self._camera= SimulatedAuxiliaryCamera('qfs')
        self._rpcHandler= MyRpcHandler()
        self._replySocket= MyReplySocket()
        self._publisherSocket= MyPublisherSocket()
        self._statusSocket= MyPublisherSocket()
        self._displaySocket= MyPublisherSocket()
        self._serverName= 'pippo'
        self._ports= 'foo'
        self._ctrl= CameraController(
            self._serverName,
            self._ports,
            self._camera,
            self._replySocket,
            self._publisherSocket,
            self._statusSocket,
            self._displaySocket,
            self._rpcHandler)


    def tearDown(self):
        self._camera.raiseExceptionOnDeinitialize(False)
        self._camera.deinitialize()


    def testPublishesStatus(self):
        self._ctrl.step()
        status= self._rpcHandler.getLastPublished(
            self._statusSocket)
        self.assertEqual(self._camera.exposureTime(),
                         status.exposureTimeInMilliSec)
        self.assertEqual(self._camera.cols(),
                         status.frameWidth)
        self.assertEqual(self._camera.dtype(),
                         status.dtype)


    def testReadCameraStatusOnlyIfNeeded(self):
        self._ctrl.setBinning(1)
        self._ctrl.step()
        status= self._rpcHandler.getLastPublished(
            self._statusSocket)
        self._ctrl.step()
        status2= self._rpcHandler.getLastPublished(
            self._statusSocket)
        self.assertEqual(status, status2)
        self._ctrl.setBinning(2)
        self._ctrl.step()
        status3= self._rpcHandler.getLastPublished(
            self._statusSocket)
        self.assertNotEqual(status, status3)


    def testTerminate(self):
        self._camera.raiseExceptionOnDeinitialize(True)
        self._ctrl.terminate()
        self.assertTrue(self._ctrl.isTerminated())


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()