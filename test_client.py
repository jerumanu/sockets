import os
import unittest
from unittest.mock import patch, MagicMock
import socket
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from PyPDF2 import PdfReader

from client.client import main
from client.speed_test_client import create_pdf_report


class TestClientProgram(unittest.TestCase):

    @patch("socket.socket")
    def test_main_success(self, mock_socket):
        mock_client_instance = MagicMock()
        mock_socket.return_value = mock_client_instance

        # Simulate server response
        mock_response = b"Success"
        mock_client_instance.recv.return_value = mock_response

        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(("localhost", 9997))

        query_string = "25;0;1;26;0;9;5;0;"
        client.send(query_string.encode("utf-8"))

        response = client.recv(4096)

        # Close the client socket
        client.close()

        # Assert
        mock_socket.assert_called_once_with(socket.AF_INET, socket.SOCK_STREAM)
        mock_client_instance.connect.assert_called_once_with(("localhost", 9997))
        mock_client_instance.send.assert_called_once_with(query_string.encode("utf-8"))
        mock_client_instance.recv.assert_called_once_with(4096)
        self.assertEqual(response.decode("utf-8"), "Success")


class TestCreatePDFReport(unittest.TestCase):

    def test_create_pdf_report(self):
        # Sample input data for the test
        results = [
            (10000, False, 0.1234, 50.0),
            (100000, True, 0.2345, 75.0),
            (1000000, False, 0.3456, 60.0),
        ]

        create_pdf_report(results)

        # Check if the generated PDF file exists
        self.assertTrue(os.path.exists("speed_report.pdf"))

        # Open the PDF and check if it has the expected data

        with open("speed_report.pdf", "rb") as f:
            reader = PdfReader(f)
            num_pages = len(reader.pages)
            self.assertGreater(num_pages, 0)  # Ensure there's at least one page

            # Check the content of the first page
            first_page = reader.pages[0].extract_text()
            self.assertIn("File Search Algorithm Performance Report", first_page)
            self.assertIn(
                "This report presents the performance of different file search algorithms",
                first_page,
            )
            self.assertIn("10000", first_page)
            self.assertIn("False", first_page)
            self.assertIn("0.1234", first_page)
            self.assertIn("50.00", first_page)

    def tearDown(self):
        if os.path.exists("speed_report.pdf"):
            os.remove("speed_report.pdf")
            


if __name__ == "__main__":
    unittest.main()
