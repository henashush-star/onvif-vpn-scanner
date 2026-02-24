import unittest
from unittest.mock import patch, MagicMock
from onvif_scanner.inspector import CameraInspector

class TestCameraInspector(unittest.TestCase):
    @patch('onvif_scanner.inspector.ONVIFCamera')
    def test_get_device_info(self, mock_onvif_camera):
        # Setup mock
        mock_camera_instance = MagicMock()
        mock_onvif_camera.return_value = mock_camera_instance

        mock_devicemgmt = MagicMock()
        mock_camera_instance.create_devicemgmt_service.return_value = mock_devicemgmt

        mock_info = MagicMock()
        mock_info.Manufacturer = "TestMfg"
        mock_info.Model = "TestModel"
        mock_info.FirmwareVersion = "1.0"
        mock_info.SerialNumber = "12345"
        mock_devicemgmt.GetDeviceInformation.return_value = mock_info

        inspector = CameraInspector("1.2.3.4", "user", "pass")
        # Ensure we connect first or get_device_info connects
        inspector.connect()
        info = inspector.get_device_info()

        self.assertEqual(info.manufacturer, "TestMfg")
        self.assertEqual(info.model, "TestModel")

    @patch('onvif_scanner.inspector.ONVIFCamera')
    def test_get_profiles(self, mock_onvif_camera):
        mock_camera_instance = MagicMock()
        mock_onvif_camera.return_value = mock_camera_instance

        mock_media = MagicMock()
        mock_camera_instance.create_media_service.return_value = mock_media

        p1 = MagicMock()
        p1.token = "t1"
        p1.Name = "Profile1"

        mock_media.GetProfiles.return_value = [p1]

        mock_uri = MagicMock()
        mock_uri.Uri = "rtsp://test/1"
        mock_media.GetStreamUri.return_value = mock_uri

        inspector = CameraInspector("1.2.3.4", "user", "pass")
        inspector.connect()
        profiles = inspector.get_profiles()

        self.assertEqual(len(profiles), 1)
        self.assertEqual(profiles[0].name, "Profile1")
        self.assertEqual(profiles[0].rtsp_uri, "rtsp://test/1")
