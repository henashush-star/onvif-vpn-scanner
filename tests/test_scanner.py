import unittest
from unittest.mock import patch, MagicMock
import socket
from onvif_scanner.scanner import WSDiscoveryScanner, IPRangeScanner

class TestWSDiscoveryScanner(unittest.TestCase):
    @patch('socket.socket')
    def test_discover(self, mock_socket):
        # Setup mock socket
        mock_sock_instance = MagicMock()
        mock_socket.return_value = mock_sock_instance

        # Simulate one response then timeout
        mock_sock_instance.recvfrom.side_effect = [
            (b'<s:Envelope><s:Body><d:ProbeMatches><d:ProbeMatch><d:XAddrs>http://192.168.1.100/onvif/device_service</d:XAddrs></d:ProbeMatch></d:ProbeMatches></s:Body></s:Envelope>', ('192.168.1.100', 3702)),
            socket.timeout
        ]

        scanner = WSDiscoveryScanner()
        ips = scanner.discover(retries=0, timeout=0.1)

        self.assertIn('192.168.1.100', ips)

class TestIPRangeScanner(unittest.TestCase):
    def test_check_onvif(self):
        scanner = IPRangeScanner("10.0.0.0/24")

        with patch('socket.socket') as mock_socket, \
             patch('onvif_scanner.scanner.requests.get') as mock_get:

            mock_sock_instance = MagicMock()
            mock_socket.return_value.__enter__.return_value = mock_sock_instance
            mock_sock_instance.connect_ex.return_value = 0

            # Test 200 OK
            mock_get.return_value.status_code = 200
            self.assertTrue(scanner._check_onvif("192.168.1.10", 1.0))

            # Test 404 Not Found (should be False)
            mock_get.return_value.status_code = 404
            self.assertFalse(scanner._check_onvif("192.168.1.10", 1.0))

            # Test 500 (should be True)
            mock_get.return_value.status_code = 500
            self.assertTrue(scanner._check_onvif("192.168.1.10", 1.0))

            # Test port closed
            mock_sock_instance.connect_ex.return_value = 1
            self.assertFalse(scanner._check_onvif("192.168.1.11", 1.0))

    def test_check_onvif_timeouts(self):
        scanner = IPRangeScanner("10.0.0.0/24")

        with patch('socket.socket') as mock_socket, \
             patch('onvif_scanner.scanner.requests.get') as mock_get:

            mock_sock_instance = MagicMock()
            mock_socket.return_value.__enter__.return_value = mock_sock_instance
            mock_sock_instance.connect_ex.return_value = 0

            mock_get.return_value.status_code = 200

            scan_timeout = 5.0
            scanner._check_onvif("192.168.1.10", scan_timeout)

            # Verify socket timeout was set to 0.2 (new behavior)
            mock_sock_instance.settimeout.assert_called_with(0.2)

            # Verify requests.get used scan_timeout
            mock_get.assert_called()
            args, kwargs = mock_get.call_args
            self.assertEqual(kwargs['timeout'], scan_timeout)
