import neoapi
import numpy as np
import threading
import time
from pysilico_server.devices.abstract_camera import AbstractCamera, CameraException
from plico.utils.logger import Logger
from plico.utils.decorator import override, returns
from pysilico.types.camera_frame import CameraFrame


class BaumerCamera(AbstractCamera):

    def __init__(self, name, serial_number=None, ip_address=None):
        self._name = name
        self._logger = Logger.of(f'BaumerCamera.{name}')
        self._camera = neoapi.Cam()
        self._serial_number = serial_number
        self._ip_address = ip_address
        self._frame_counter = 0
        self._exposure_time_ms = 10.0
        self._binning = 1
        self._is_acquiring = False
        self._callback_list = []
        self._width = 0
        self._height = 0
        self._dtype = np.uint8  # Default to Mono8

        self._connect_camera()
        self._configure_camera()

        self._acquisition_thread = None
        self._mutex = threading.RLock()

        self._logger.notice(f'Baumer camera {self._name} initialized.')


    def _connect_camera(self):
        try:
            if self._serial_number:
                self._camera.Connect(self._serial_number)
            elif self._ip_address:
                self._camera.Connect(self._ip_address)
            else:
                raise CameraException(
                    "Either serial_number or ip_address must be provided for Baumer camera."
                )
            self._width = self._camera.f.Width.value
            self._height = self._camera.f.Height.value
            self._logger.notice(
                f"Connected to Baumer camera {self._name}."
            )
        except neoapi.NeoException as e:
            self._logger.error(f"Failed to connect to Baumer camera: {e}")
            raise CameraException(f"Failed to connect to Baumer camera: {e}")

    def _configure_camera(self):
        try:
            self._camera.f.ExposureTime.Set(self._exposure_time_ms * 1000)  # neoapi uses microseconds
        except neoapi.FeatureAccessException:
            self._logger.warn("Exposure time feature not accessible. Skipping.")

        self._camera.DisableChunk()
        self._camera.SetImageBufferCount()
        self._camera.SetImageBufferCycleCount()

        try:
            self._camera.f.PixelFormat.Set(neoapi.PixelFormat_Mono12)
            self._dtype = np.uint16  # Assuming 12-bit for Mono12
            self._logger.notice("Using Mono12 pixel format")
        except neoapi.FeatureAccessException:
            self._logger.warn("Mono12 pixel format not supported, trying BGR8")
            try:
                self._camera.f.PixelFormat.Set(neoapi.PixelFormat_BGR8)
                self._dtype = np.uint8  # Assuming 8-bit for BGR8
                self._logger.notice("Using RGB pixel format")
            except neoapi.FeatureAccessException:
                self._logger.warn("BGR8 pixel format not supported, trying Mono8")
                try:
                    self._camera.f.PixelFormat.Set(neoapi.PixelFormat_Mono8)
                    self._dtype = np.uint8  # Assuming 8-bit for Mono8
                    self._logger.notice("Using Mono8 pixel format")
                except neoapi.FeatureAccessException as e:
                    self._logger.error(
                        f"Neither Mono12, BGR8, nor Mono8 pixel format supported: {e}"
                    )
                    raise CameraException(
                        f"Unsupported pixel formats: {e}"
                    )

        self._camera.f.TriggerMode.value = neoapi.TriggerMode_On


    @override
    def name(self):
        return self._name

    @override
    @returns(CameraFrame)
    def readFrame(self, timeoutMilliSec=2000):
        with self._mutex:
            if not self._is_acquiring:
                self.startAcquisition()
            self._camera.f.TriggerSoftware.Execute()
            image = self._camera.GetImage()
            while image.IsEmpty():
                time.sleep(0.01)  # Small delay to avoid busy-waiting
                image = self._camera.GetImage()

            if not image.IsEmpty():
                self._frame_counter += 1
                np_array = image.GetNPArray()
                if hasattr(self, '_rois') and self._rois:
                    # PYSILICO-1: ROI Management - Return the first ROI as a single frame for compatibility
                    # PYSILICO-2: Data Access - All ROIs are accessible via get_roi_frames
                    first_roi = self._rois[0]
                    x, y, width, height = first_roi['x'], first_roi['y'], first_roi['width'], first_roi['height']
                    return CameraFrame(np_array[y:y + height, x:x + width], counter=self._frame_counter)
                else:
                    return CameraFrame(np_array, counter=self._frame_counter)
            else:
                raise CameraException("Failed to acquire image from Baumer camera.")

    def get_roi_frames(self):
        """
        Returns a dictionary of ROI images if ROIs are defined, otherwise returns an empty dictionary.
        """
        with self._mutex:
            if not self._is_acquiring:
                self.startAcquisition()
            self._camera.f.TriggerSoftware.Execute()
            image = self._camera.GetImage()
            while image.IsEmpty():
                time.sleep(0.01)
                image = self._camera.GetImage()
            
            if not image.IsEmpty():
                np_array = image.GetNPArray()
                if hasattr(self, '_rois') and self._rois:
                    roi_images = {}
                    for roi in self._rois:
                        x, y, width, height = roi['x'], roi['y'], roi['width'], roi['height']
                        name = roi.get('name', f"ROI_{x}_{y}_{width}_{height}")
                        roi_images[name] = CameraFrame(np_array[y:y + height, x:x + width], counter=self._frame_counter)
                    return roi_images
                else:
                    return {}
            else:
                raise CameraException("Failed to acquire image from Baumer camera for ROIs.")

    @override
    def rows(self):
        return self._height

    @override
    def cols(self):
        return self._width

    @override
    def dtype(self):
        return self._dtype

    @override
    def setExposureTime(self, exposureTimeInMilliSeconds):
        with self._mutex:
            self._exposure_time_ms = exposureTimeInMilliSeconds
            try:
                self._camera.f.ExposureTime.Set(self._exposure_time_ms * 1000)
            except neoapi.FeatureAccessException:
                self._logger.warn("Exposure time feature not accessible. Cannot set.")

    @override
    def exposureTime(self):
        with self._mutex:
            try:
                return self._camera.f.ExposureTime.value / 1000.0
            except neoapi.FeatureAccessException:
                self._logger.warn("Exposure time feature not accessible. Returning stored value.")
                return self._exposure_time_ms

    @override
    def setBinning(self, binning):
        with self._mutex:
            self._logger.warn("Binning not directly supported by neoapi for Baumer camera. Software binning can be implemented if needed.")
            self._binning = binning

    @override
    def getBinning(self):
        return self._binning

    @override
    def registerCallback(self, callback):
        with self._mutex:
            self._callback_list.append(callback)

    def _acquisition_loop(self):
        while self._is_acquiring:
            try:
                frame = self.readFrame()
                with self._mutex:
                    for callback in self._callback_list:
                        callback(frame)
            except CameraException as e:
                self._logger.error(f"Error during acquisition: {e}")
            time.sleep(0.001) # Avoid busy loop

    @override
    def startAcquisition(self):
        with self._mutex:
            if not self._is_acquiring:
                self._is_acquiring = True
                self._acquisition_thread = threading.Thread(target=self._acquisition_loop)
                self._acquisition_thread.start()
                self._logger.notice("Baumer camera acquisition started.")

    @override
    def stopAcquisition(self):
        with self._mutex:
            if self._is_acquiring:
                self._is_acquiring = False
                if self._acquisition_thread:
                    self._acquisition_thread.join()
                    self._acquisition_thread = None
                self._logger.notice("Baumer camera acquisition stopped.")

    @override
    def getFrameCounter(self):
        with self._mutex:
            return self._frame_counter

    @override
    def getFrameRate(self):
        # TODO: Implement actual frame rate measurement
        return 1000.0 / self.exposureTime() if self.exposureTime() > 0 else 0

    @override
    def setFrameRate(self, frameRateInHz):
        self._logger.warn("Setting frame rate not directly supported. Adjust exposure time instead.")
        # Optional: calculate exposure time from frame rate and set it.
        if frameRateInHz > 0:
            self.setExposureTime(1000.0 / frameRateInHz)

    @override
    def deinitialize(self):
        with self._mutex:
            self.stopAcquisition()
            self._camera.Disconnect()
            self._logger.notice("Baumer camera deinitialized.")

    @override
    def setParameter(self, name, value):
        self._logger.warn(f"Setting device specific parameter {name} not yet implemented for Baumer camera.")
        # TODO: Implement setting specific neoapi features

    @override
    def getParameters(self):
        self._logger.warn("Getting device specific parameters not yet implemented for Baumer camera.")
        return {}

    # PYSILICO-1: ROI Management
    def set_rois(self, rois):
        """
        Sets the regions of interest for the camera.
        `rois` should be a list of dictionaries, where each dictionary
        defines an ROI with keys like 'x', 'y', 'width', 'height', 'name'.
        """
        for roi in rois:
            if not all(k in roi for k in ['x', 'y', 'width', 'height']):
                raise ValueError("Each ROI must have 'x', 'y', 'width', and 'height' keys.")
        self._rois = rois
        self._logger.notice(f"ROIs set to: {rois}")

    def get_rois(self):
        """
        Returns the currently configured regions of interest.
        """
        return getattr(self, '_rois', [])

    def clear_rois(self):
        """
        Clears all defined regions of interest.
        """
        if hasattr(self, '_rois'):
            del self._rois
        self._logger.notice("ROIs cleared.")
