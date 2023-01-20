#!/usr/bin/env python
import os
import sys
import subprocess
import shutil
import unittest
import logging
import numpy as np
from test.test_helper import TestHelper, Poller, MessageInFileProbe, \
    ExecutionProbe
from plico.utils.configuration import Configuration
from plico.rpc.zmq_remote_procedure_call import ZmqRemoteProcedureCall
from plico.utils.logger import Logger
from plico.rpc.sockets import Sockets
from plico.rpc.zmq_ports import ZmqPorts
from pysilico_server.utils.constants import Constants
from pysilico_server.utils.starter_script_creator import StarterScriptCreator
from pysilico_server.utils.process_startup_helper import ProcessStartUpHelper
from pysilico_server.process_monitor.runner import Runner as ProcessMonitorRunner
from pysilico_server.camera_controller.runner import Runner
from pysilico.client.camera_client import CameraClient
from pysilico.client.abstract_camera_client import SnapshotEntry
from pysilico_server.devices.simulated_auxiliary_camera import \
    SimulatedAuxiliaryCamera


@unittest.skipIf(sys.platform == "win32",
                 "Integration test doesn't run on Windows. Fix it!")
class IntegrationTest(unittest.TestCase):

    TEST_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                            "./tmp/")
    LOG_DIR = os.path.join(TEST_DIR, "log")
    CONF_FILE = 'test/integration/conffiles/pysilico_server.conf'
    CALIB_FOLDER = 'test/integration/calib'
    CONF_SECTION = Constants.PROCESS_MONITOR_CONFIG_SECTION
    PROCESS_MONITOR_LOG_PATH = os.path.join(LOG_DIR, "%s.log" % CONF_SECTION)
    SERVER_1_LOG_PATH = os.path.join(
        LOG_DIR, '%s%d.log' % (Constants.SERVER_CONFIG_SECTION_PREFIX, 1))
    SERVER_2_LOG_PATH = os.path.join(
        LOG_DIR, '%s%d.log' % (Constants.SERVER_CONFIG_SECTION_PREFIX, 2))
    SERVER_3_LOG_PATH = os.path.join(
        LOG_DIR, '%s%d.log' % (Constants.SERVER_CONFIG_SECTION_PREFIX, 3))

    BIN_DIR = os.path.join(TEST_DIR, "apps", "bin")
    SOURCE_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                              "../..")

    def setUp(self):
        self._setUpBasicLogging()
        self.server = None
        self._wasSuccessful = False

        self._removeTestFolderIfItExists()
        self._makeTestDir()
        self.configuration = Configuration()
        self.configuration.load(self.CONF_FILE)
        self.rpc = ZmqRemoteProcedureCall()

        calibrationRootDir = self.configuration.calibrationRootDir()
        self._setUpCalibrationTempFolder(calibrationRootDir)

    def _setUpBasicLogging(self):
        logging.basicConfig(level=logging.DEBUG)
        self._logger = Logger.of('Integration Test')

    def _makeTestDir(self):
        os.makedirs(self.TEST_DIR)
        os.makedirs(self.LOG_DIR)
        os.makedirs(self.BIN_DIR)

    def _setUpCalibrationTempFolder(self, calibTempFolder):
        shutil.copytree(self.CALIB_FOLDER,
                        calibTempFolder)

    def _removeTestFolderIfItExists(self):
        if os.path.exists(self.TEST_DIR):
            shutil.rmtree(self.TEST_DIR)

    def tearDown(self):
        TestHelper.dumpFileToStdout(self.PROCESS_MONITOR_LOG_PATH)
        TestHelper.dumpFileToStdout(self.SERVER_1_LOG_PATH)
        TestHelper.dumpFileToStdout(self.SERVER_2_LOG_PATH)
        TestHelper.dumpFileToStdout(self.SERVER_3_LOG_PATH)

        if self.server is not None:
            TestHelper.terminateSubprocess(self.server)

        if self._wasSuccessful:
            self._removeTestFolderIfItExists()

    def _createStarterScripts(self):
        ssc = StarterScriptCreator()
        ssc.setInstallationBinDir(self.BIN_DIR)
        ssc.setPythonPath(self.SOURCE_DIR)
        ssc.setConfigFileDestination(self.CONF_FILE)
        numCameras = len(self.configuration.numberedSectionList(
            Constants.SERVER_CONFIG_SECTION_PREFIX))
        ssc.installExecutables(numCameras)

    def _startProcesses(self):
        psh = ProcessStartUpHelper()
        self.server = subprocess.Popen(
            [psh.processProcessMonitorStartUpScriptPath(),
             self.CONF_FILE,
             self.CONF_SECTION])
        Poller(5).check(MessageInFileProbe(
            ProcessMonitorRunner.RUNNING_MESSAGE, self.PROCESS_MONITOR_LOG_PATH))

    def _testProcessesActuallyStarted(self):
        Poller(5).check(MessageInFileProbe(
            Runner.RUNNING_MESSAGE, self.SERVER_1_LOG_PATH))
        Poller(5).check(MessageInFileProbe(
            Runner.RUNNING_MESSAGE, self.SERVER_2_LOG_PATH))
        Poller(5).check(MessageInFileProbe(
            Runner.RUNNING_MESSAGE, self.SERVER_3_LOG_PATH))

    def _buildClients(self):
        ports1 = ZmqPorts.fromConfiguration(
            self.configuration,
            '%s%d' % (Constants.SERVER_CONFIG_SECTION_PREFIX, 1))
        self.client1 = CameraClient(
            self.rpc, Sockets(ports1, self.rpc))
        ports2 = ZmqPorts.fromConfiguration(
            self.configuration,
            '%s%d' % (Constants.SERVER_CONFIG_SECTION_PREFIX, 2))
        self.client2 = CameraClient(
            self.rpc, Sockets(ports2, self.rpc))
        ports3 = ZmqPorts.fromConfiguration(
            self.configuration,
            '%s%d' % (Constants.SERVER_CONFIG_SECTION_PREFIX, 3))
        self.client3 = CameraClient(
            self.rpc, Sockets(ports3, self.rpc))

    def _checkBackdoor(self):
        self.client1.execute(
            "import numpy as np; "
            "self._myarray= np.array([1, 2])")
        self.assertEqual(
            repr(np.array([1, 2])),
            self.client1.eval("self._myarray"))
        self.client1.execute("self._foobar= 42")
        self.assertEqual(
            "42",
            self.client1.eval("self._foobar"))

    def _testGetSnapshot(self):
        snapshot = self.client1.getSnapshot('aa')
        snKey = 'aa.%s' % SnapshotEntry.CAMERA_NAME
        self.assertEqual('Simulated Aux Camera', snapshot[snKey])

    def _testServerInfo(self):
        serverInfo = self.client1.serverInfo()
        self.assertEqual('AVT 1 server',
                         serverInfo.name)
        self.assertEqual('localhost', serverInfo.hostname)

    def _testCameraGetFrame(self):
        self._applyCameraBinning(self.client1, 1)
        cameraFrame = self.client1.getFutureFrames(1)
        frame = cameraFrame.toNumpyArray()
        counter = cameraFrame.counter()

        self.assertEqual(frame.shape,
                         (SimulatedAuxiliaryCamera.SENSOR_H,
                          SimulatedAuxiliaryCamera.SENSOR_W))

        counter2 = self.client1.getFutureFrames(1).counter()
        counter3 = self.client1.getFutureFrames(1).counter()
        self.assertTrue(counter2 > counter)
        self.assertTrue(counter3 > counter2)

    def _testCameraGetFutureFrames(self):
        self._applyCameraBinning(self.client1, 1)
        cameraFrame = self.client1.getFutureFrames(10)
        frame = cameraFrame.toNumpyArray()
        counter = cameraFrame.counter()

        self.assertEqual(
            frame.shape,
            (SimulatedAuxiliaryCamera.SENSOR_H,
             SimulatedAuxiliaryCamera.SENSOR_W, 10))
        self.assertEqual(float, frame.dtype)
        self.assertNotEqual(0,
                            np.std(frame[0, 0, :]))

        counter2 = self.client1.getFutureFrames(1).counter()
        self.assertTrue(counter2 > counter)

    def _testCameraModifyExposureTime(self):
        self.client1.setExposureTime(3.5)
        Poller(3).check(ExecutionProbe(
            lambda: self.assertEqual(3.5,
                                     self.client1.exposureTime())))
        self.client1.setExposureTime(0.75)
        Poller(3).check(ExecutionProbe(
            lambda: self.assertEqual(0.75,
                                     self.client1.exposureTime())))

    def _testCameraBinning(self):
        self._applyCameraBinning(self.client1, 1)
        shape1 = self.client1.getFutureFrames(1).toNumpyArray().shape
        Poller(3).check(ExecutionProbe(
            lambda: self.assertEqual(1,
                                     self.client1.getBinning())))
        self._applyCameraBinning(self.client1, 4)
        shape4 = self.client1.getFutureFrames(1).toNumpyArray().shape
        Poller(3).check(ExecutionProbe(
            lambda: self.assertEqual(4,
                                     self.client1.getBinning())))
        self.assertEqual(shape1[0] / 4, shape4[0])
        self.assertEqual(shape1[1] / 4, shape4[1])
        self._applyCameraBinning(self.client1, 1)

    def _applyCameraBinning(self, cameraClient, binning):
        cameraClient.setBinning(binning)
        # NOTNEEDED _trashLast= cameraClient.getFutureFrames(1)

    def _testFrameForDisplayIsResizedUnlessBinned(self):
        self._applyCameraBinning(self.client1, 1)
        disp = self.client1.getFrameForDisplay().toNumpyArray().shape
        full = self.client1.getFutureFrames(1).toNumpyArray().shape
        self.assertTrue(full[0] > disp[0])

        self._applyCameraBinning(self.client1, 8)
        disp = self.client1.getFrameForDisplay().toNumpyArray().shape
        full = self.client1.getFutureFrames(1).toNumpyArray().shape
        Poller(3).check(ExecutionProbe(
            lambda: self.assertEqual(
                full,
                self.client1.getFrameForDisplay().toNumpyArray().shape)))

    def testMain(self):
        self._buildClients()
        self._createStarterScripts()
        self._startProcesses()
        self._testProcessesActuallyStarted()
        self._testCameraGetFrame()
        self._testCameraGetFutureFrames()
        self._testCameraModifyExposureTime()
        self._testCameraBinning()
        self._testFrameForDisplayIsResizedUnlessBinned()
        self._testGetSnapshot()
        self._testServerInfo()
        self._checkBackdoor()
        self._wasSuccessful = True


if __name__ == "__main__":
    unittest.main()
