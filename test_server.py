import os
import unittest
import socket

from PyPDF2 import PdfReader
from server.server import (
    MAX_STRING_LENGTH,
    binary_search_in_file,
    get_config_options,
    load_file_to_cache,
    handle_client,
)
from unittest.mock import Mock, patch

from benchmark_search import (
    generate_pdf_report,
    python_naive_search,
    python_set_search,
    grep_search,
    awk_search,
    binary_search,
    benchmark_search_methods,
)


class BaseTestConfig(unittest.TestCase):
    def setUp(self):
        self.config_file_valid = "test_config.cfg"
        self.config_file_missing_key = "test_config2.cfg"

        with open(self.config_file_valid, "w") as f:
            f.write("linuxpath=/path/to/file\nREREAD_ON_QUERY=True\n")

        with open(self.config_file_missing_key, "w") as f:
            f.write("REREAD_ON_QUERY=True\n")

    def tearDown(self):
        try:
            os.remove(self.config_file_valid)
            os.remove(self.config_file_missing_key)
        except FileNotFoundError:
            pass


class TestConfigOptions(BaseTestConfig):

    def test_valid_config(self):
        file_path, reread_on_query, ssl_enabled, certfile, keyfile = get_config_options(
            self.config_file_valid
        )
        self.assertEqual(file_path, "/path/to/file")
        self.assertTrue(reread_on_query)

    def test_missing_key(self):
        file_path, reread_on_query, ssl_enabled, certfile, keyfile = get_config_options(
            self.config_file_missing_key
        )
        self.assertIsNone(file_path)
        self.assertTrue(reread_on_query)

    def test_file_not_found(self):
        # Here we simulate a missing file without raising an exception
        file_path, reread_on_query, ssl_enabled, certfile, keyfile = get_config_options(
            "nonexistent_file.cfg"
        )
        self.assertIsNone(file_path)
        self.assertFalse(reread_on_query)


class TestLoadFileToCache(unittest.TestCase):

    def setUp(self):
        self.valid_file = "test_valid_file.txt"
        self.empty_file = "test_empty_file.txt"
        self.special_chars_file = "test_special_chars_file.txt"

        with open(self.valid_file, "w") as f:
            f.write("line1\nline2\nline3\n")

        with open(self.empty_file, "w") as f:
            pass  # Empty file

        with open(self.special_chars_file, "w") as f:
            f.write("line with special chars!@#$%^&*\nline with \t tabs\n")

    def tearDown(self):
        for file in [self.valid_file, self.empty_file, self.special_chars_file]:
            if os.path.exists(file):
                os.remove(file)

    def test_load_valid_file(self):
        cached_lines = load_file_to_cache(self.valid_file)
        expected_lines = {"line1", "line2", "line3"}
        self.assertEqual(cached_lines, expected_lines)

    def test_load_empty_file(self):
        cached_lines = load_file_to_cache(self.empty_file)
        self.assertEqual(cached_lines, set())

    def test_file_not_found(
        self,
    ):
        cached_lines = load_file_to_cache("nonexistent_file.txt")
        self.assertEqual(cached_lines, set())

    def test_file_with_special_chars(self):
        cached_lines = load_file_to_cache(self.special_chars_file)
        expected_lines = {"line with special chars!@#$%^&*", "line with \t tabs"}
        self.assertEqual(cached_lines, expected_lines)


class TestSearchStringInFile(unittest.TestCase):

    def setUp(self):
        self.valid_file = "test_valid_file.txt"
        self.special_chars_file = "test_special_chars_file.txt"

        with open(self.valid_file, "w") as f:
            f.write("line1\nline2\nline3\n")

        with open(self.special_chars_file, "w") as f:
            f.write("line with special chars!@#$%^&*\nline with \t tabs\n")

        self.cached_lines = load_file_to_cache(self.valid_file)

    def tearDown(self):
        for file in [self.valid_file, self.special_chars_file]:
            if os.path.exists(file):
                os.remove(file)

    def test_string_exists_with_caching(self):
        result, exec_time = binary_search_in_file(
            self.valid_file,
            "line2",
            reread_on_query=False,
            cached_lines=self.cached_lines,
        )
        self.assertTrue(result)
        self.assertGreater(exec_time, 0)

    def test_string_exists_without_caching(self):
        result, exec_time = binary_search_in_file(
            self.valid_file, "line3", reread_on_query=True, cached_lines=None
        )
        self.assertTrue(result)
        self.assertGreater(exec_time, 0)

    def test_string_does_not_exist(self):
        result, exec_time = binary_search_in_file(
            self.valid_file,
            "nonexistent_line",
            reread_on_query=False,
            cached_lines=self.cached_lines,
        )
        self.assertFalse(result)
        self.assertGreater(exec_time, 0)


class MockSocket:
    def __init__(self, recv_data, peer_name=("127.0.0.1", 12345)):
        self.recv_data = recv_data
        self.sent_data = b""
        self.closed = False
        self.peer_name = peer_name

    def recv(self, bufsize):
        return self.recv_data

    def send(self, data):
        self.sent_data += data

    def close(self):
        self.closed = True

    def getpeername(self):
        return self.peer_name


class TestHandleClient(unittest.TestCase):

    def setUp(self):
        self.test_file = "test_file.txt"
        with open(self.test_file, "w") as f:
            f.write("search_term\nanother_term\n")
        self.cached_lines = load_file_to_cache(self.test_file)

    def tearDown(self):
        if os.path.exists(self.test_file):
            os.remove(self.test_file)

    def test_connection_reset(self):
        mock_socket = MockSocket(b"")

        handle_client(mock_socket, self.test_file, False, cached_lines=None)
        self.assertEqual(mock_socket.sent_data, b"")
        self.assertTrue(mock_socket.closed)


class TestSearchAlgorithms(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Create a temporary test file to use across multiple tests
        cls.test_file = "test_data.txt"
        with open(cls.test_file, "w") as f:
            for i in range(1, 10001):
                f.write(
                    f"line_{i:05d}\n"
                )  # Write lines as line_00001, line_00002, etc.

    @classmethod
    def tearDownClass(cls):
        # Remove the test file after all tests are run
        if os.path.exists(cls.test_file):
            os.remove(cls.test_file)

    def test_python_naive_search(self):
        exec_time = python_naive_search(self.test_file, "line_00500")
        self.assertGreater(exec_time, 0, "Execution time should be greater than 0")

    def test_python_set_search(self):
        exec_time = python_set_search(self.test_file, "line_00500")
        self.assertGreater(exec_time, 0, "Execution time should be greater than 0")

    def test_grep_search(self):
        exec_time = grep_search(self.test_file, "line_00500")
        self.assertGreater(exec_time, 0, "Execution time should be greater than 0")

    def test_awk_search(self):
        exec_time = awk_search(self.test_file, "line_00500")
        self.assertGreater(exec_time, 0, "Execution time should be greater than 0")

    def test_binary_search(self):
        exec_time = binary_search(self.test_file, "line_00500")
        self.assertGreater(exec_time, 0, "Execution time should be greater than 0")

    def test_benchmark_search_methods(self):
        results = benchmark_search_methods(self.test_file, "line_00500")
        self.assertIn(
            "Python Naive",
            results,
            "Benchmark results should include Python Naive method",
        )
        self.assertIn(
            "Python Set", results, "Benchmark results should include Python Set method"
        )
        self.assertIn(
            "Grep Search",
            results,
            "Benchmark results should include Grep Search method",
        )
        self.assertIn(
            "Awk Search", results, "Benchmark results should include Awk Search method"
        )
        self.assertIn(
            "Binary Search (sorted files)",
            results,
            "Benchmark results should include Binary Search method",
        )
        for method, exec_time in results.items():
            self.assertGreater(
                exec_time, 0, f"{method} execution time should be greater than 0"
            )


class TestQueryStringUtils(unittest.TestCase):

    def test_whitespace_stripping(self):
        request = b"  query string  "
        expected_query_string = "query string"
        query_string = request.replace(b"\x00", b"").decode("utf-8").strip()
        self.assertEqual(query_string, expected_query_string)

    def test_multiple_null_bytes(self):
        request = b"foo\x00bar\x00baz"
        expected_query_string = "foo bar baz"
        query_string = request.replace(b"\x00", b" ").decode("utf-8").strip()
        self.assertEqual(query_string, expected_query_string)

    def test_null_byte_removal(self):
        request = b"hello\x00world"
        expected_query_string = "hello world"
        query_string = request.replace(b"\x00", b" ").decode("utf-8").strip()
        self.assertEqual(query_string, expected_query_string)

    def test_empty_string(self):
        request = b""
        expected_query_string = ""
        query_string = request.replace(b"\x00", b"").decode("utf-8").strip()
        self.assertEqual(query_string, expected_query_string)

    def test_non_ascii_characters(self):
        request = b"\xe4\xb8\xad\xe6\x96\x87"  # Chinese characters
        expected_query_string = "\u4e2d\u6587"
        query_string = request.replace(b"\x00", b"").decode("utf-8").strip()
        self.assertEqual(query_string, expected_query_string)


class TestGeneratePDFReport(unittest.TestCase):

    def test_generate_pdf_report(self):
        # Sample input data for the test
        results = {"Algorithm A": 0.1234, "Algorithm B": 0.2345, "Algorithm C": 0.3456}
        file_path = "test_report.pdf"

        # Call the function under test
        generate_pdf_report(results, file_path)

        # Check if the generated PDF file exists
        self.assertTrue(os.path.exists(file_path))

        # Open the PDF and check if it has the expected data
        with open(file_path, "rb") as f:
            reader = PdfReader(f)
            num_pages = len(reader.pages)
            self.assertGreater(num_pages, 0)

            first_page = reader.pages[0].extract_text()
            self.assertIn("File Search Algorithm Performance Report", first_page)
            self.assertIn(
                "This report presents the performance of different file search algorithms.",
                first_page,
            )
            self.assertIn("Algorithm A", first_page)
            self.assertIn("0.1234", first_page)
            self.assertIn("Algorithm B", first_page)
            self.assertIn("0.2345", first_page)
            self.assertIn("Algorithm C", first_page)
            self.assertIn("0.3456", first_page)

    def tearDown(self):
        # Cleanup the generated PDF after the test
        if os.path.exists("test_report.pdf"):
            os.remove("test_report.pdf")


if __name__ == "__main__":
    unittest.main()
