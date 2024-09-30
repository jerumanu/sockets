import io
import logging
import unittest
from unittest import mock
from unittest.mock import MagicMock, patch
from server.server import start_server


class TestStartServer(unittest.TestCase):

    @patch("server.server.socket.socket")
    @patch("server.server.ssl.create_default_context")
    @patch("server.server.load_file_to_cache")
    @patch("server.server.get_config_options")
    def test_start_server_with_ssl_missing_certificates(
        self, mock_get_config, mock_load_file, mock_create_context, mock_socket
    ):
        # Mocking the return values
        mock_get_config.return_value = ("valid_file.txt", True, True, None, None)

        # Call the function
        start_server("config_file.ini")

        mock_get_config.assert_called_once_with("config_file.ini")
        mock_socket.assert_called_once()
        self.assertFalse(mock_load_file.called)  # Should not be called
        mock_create_context.assert_not_called()  # SSL context should not be created

    @patch("server.server.socket.socket")
    @patch("server.server.get_config_options")
    def test_start_server_with_no_file_path(self, mock_get_config, mock_socket):
        # Mocking the return values
        mock_get_config.return_value = (None, True, False, None, None)

        start_server("config_file.ini")

        mock_get_config.assert_called_once_with("config_file.ini")
        mock_socket.assert_not_called()


if __name__ == "__main__":
    unittest.main()
