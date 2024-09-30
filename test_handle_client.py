import socket
import time
import logging
import unittest
from unittest.mock import patch, Mock, call

from server.server import (
    handle_client,
    binary_search_in_file,
    BUFFER_SIZE,
    MAX_STRING_LENGTH,
)


class TestHandleClient(unittest.TestCase):
    @patch("server.server.binary_search_in_file")
    @patch("server.server.logging.debug")
    @patch("server.server.logging.error")
    def test_handle_valid_query(self, mock_error, mock_debug, mock_binary_search):
        # Mock socket behavior
        mock_client_socket = Mock(spec=socket.socket)
        # Configure getpeername to return a tuple with an IP address
        mock_client_socket.getpeername.return_value = ("127.0.0.1", 12345)
        mock_client_socket.recv.side_effect = [
            b"valid_query", 
            b"",  
        ]
        mock_binary_search.return_value = True, 0.1234

        # Call the function
        handle_client(mock_client_socket, "test_file.txt", False, None)

        # Assertions
        mock_client_socket.recv.assert_called_with(BUFFER_SIZE)
        mock_binary_search.assert_called_once_with(
            "test_file.txt", "valid_query", False, None
        )
      
        mock_client_socket.send.assert_called_once_with(
            b"STRING EXISTS (Execution Time: 0.1234 seconds)\n"
        )

    @patch("server.server.binary_search_in_file")
    @patch("server.server.logging.debug")
    @patch("server.server.logging.error")
    def test_handle_long_query(self, mock_error, mock_debug, mock_binary_search):
        # Mock socket behavior using side effect to simulate recv() returning a long query
        long_query = b"a" * (MAX_STRING_LENGTH + 10)  # Simulate a long query
        mock_client_socket = Mock(spec=socket.socket)

        # Configure getpeername to return a tuple with an IP address
        mock_client_socket.getpeername.return_value = ("127.0.0.1", 12345)
        mock_client_socket.recv.side_effect = [
            long_query,  
            b"",  
        ]

        # Call the function
        handle_client(mock_client_socket, "test_file.txt", False, None)

        # Assertions
        mock_client_socket.recv.assert_called_with(
            1024
        )  # Check if recv was called with BUFFER_SIZE
        mock_binary_search.assert_not_called() 

        # Create the expected truncated query message for assertion
        truncated_query = (
            long_query.decode("utf-8")[:50] + "... (truncated)"
        ) 
        mock_error.assert_called_once_with(f"Query string too long: {truncated_query}")
        mock_client_socket.send.assert_called_once_with(
            b"ERROR: Query string too long.\n"
        )

    @patch("server.server.binary_search_in_file")
    @patch("server.server.logging.debug")
    @patch("server.server.logging.error")
    def test_handle_non_existent_query(
        self, mock_error, mock_debug, mock_binary_search
    ):
        # Mock data
        mock_client_socket = Mock(spec=socket.socket)
        # Configure getpeername to return a tuple with an IP address
        mock_client_socket.getpeername.return_value = ("127.0.0.1", 12345)
        mock_client_socket.recv.side_effect = [
            b"non_existent_query",  # Simulating the query received
            b"",  # Simulating client closure after one query
        ]
        mock_binary_search.return_value = None, 0.1234

        # Call the function
        handle_client(mock_client_socket, "test_file.txt", False, None)

        # Assertions
        self.assertEqual(
            mock_client_socket.recv.call_count, 2
        )  # Expecting recv to be called twice
        mock_binary_search.assert_called_once_with(
            "test_file.txt", "non_existent_query", False, None
        )
        mock_error.assert_not_called()
        mock_client_socket.send.assert_called_once_with(
            b"STRING NOT FOUND (Execution Time: 0.1234 seconds)\n"
        )

    @patch("server.server.binary_search_in_file")
    @patch("server.server.logging.debug")
    @patch("server.server.logging.error")
    def test_handle_connection_reset_error(
        self,
        mock_error,
        mock_debug,
        mock_binary_search,
    ):
        # Mock data
        mock_client_socket = Mock(spec=socket.socket)
        mock_client_socket.recv.side_effect = (
            ConnectionResetError  # Simulate a connection reset error
        )

        # Call the function
        handle_client(mock_client_socket, "test_file.txt", False, None)

        # Assertions
        mock_client_socket.recv.assert_called_once_with(BUFFER_SIZE)
        mock_binary_search.assert_not_called()
        mock_debug.assert_called_once_with("Connection closed by the client.")
        mock_error.assert_not_called()
        mock_client_socket.send.assert_not_called()

    @patch("server.server.binary_search_in_file")
    @patch("server.server.logging.debug")
    @patch("server.server.logging.error")
    def test_handle_cached_lines_usage(
        self,
        mock_error,
        mock_debug,
        mock_binary_search,
    ):
        mock_client_socket = Mock(spec=socket.socket)
        # Configure getpeername to return a tuple with an IP address
        mock_client_socket.getpeername.return_value = ("127.0.0.1", 12345)
        mock_client_socket.recv.side_effect = [
            b"hello world", 
            b"",  
        ]
        mock_binary_search.return_value = True, 0.1234
        cached_lines = {"hello world"} 

        handle_client(mock_client_socket, "test_file.txt", False, cached_lines)

        mock_client_socket.recv.assert_called() 
        assert mock_client_socket.recv.call_count == 2
        mock_binary_search.assert_called_once_with(
            "test_file.txt", "hello world", False, cached_lines
        )

        mock_client_socket.send.assert_called_once_with(
            b"STRING EXISTS (Execution Time: 0.1234 seconds)\n"
        )

    @patch("server.server.binary_search_in_file")
    @patch("server.server.logging.debug")
    @patch("server.server.logging.error")
    def test_handle_reread_on_query_true(
        self, mock_error, mock_debug, mock_binary_search
    ):
        # Mock data
        mock_client_socket = Mock(spec=socket.socket)
        mock_client_socket.getpeername.return_value = ("127.0.0.1", 12345)
        mock_client_socket.recv.side_effect = [
            b"hello world",  
            b"",
        ]

        mock_binary_search.return_value = True, 0.1234

        # Call the function with reread_on_query=True
        handle_client(mock_client_socket, "test_file.txt", True, None)

        # Assertions
        mock_client_socket.recv.assert_called()  
        assert mock_client_socket.recv.call_count == 2 
        mock_binary_search.assert_called_once_with(
            "test_file.txt", "hello world", True, None
        )
        mock_client_socket.send.assert_called_once_with(
            b"STRING EXISTS (Execution Time: 0.1234 seconds)\n"
        )
