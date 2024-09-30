import socket
import time
import statistics
import configparser
from typing import NoReturn
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph


def update_config(reread_on_query: bool) -> None:
    """
    Updates the server configuration file to set REREAD_ON_QUERY.

    Args:
        reread_on_query (bool): Whether to reread the file on each query or not.
    """
    config = configparser.ConfigParser()
    config.read("server_config.cfg")
    config["DEFAULT"]["REREAD_ON_QUERY"] = "true" if reread_on_query else "false"
    with open("server_config.cfg", "w") as configfile:
        config.write(configfile)


def run_queries(file_size: int, query_string: str, num_queries: int) -> (float, float):
    """
    Sends multiple queries to the server and measures the response time.

    Args:
        file_size (int): The magnitude of the polled file.
        query_string (str): A string that will be queried in the file.
        num_queries (int): The number of times to issue a query.

    Returns:
        tuple: Average response time and queries per second.
    """
    latencies = []

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect(("localhost", 9997))

        for _ in range(num_queries):
            start_time = time.time()
            sock.send(query_string.encode("utf-8"))
            response = sock.recv(4096)
            exec_time = time.time() - start_time
            latencies.append(exec_time)

    avg_time = statistics.mean(latencies)
    queries_per_second = num_queries / sum(latencies)
    return avg_time, queries_per_second


def create_pdf_report(results: list) -> None:
    """
    Creates a PDF report of the speed test results.

    Args:
        results -- list of tuples (file size, REREAD_ON_QUERY status, average response time, queries per second)
    """
    pdf_file = "speed_report.pdf"
    doc = SimpleDocTemplate(pdf_file, pagesize=letter)
    styles = getSampleStyleSheet()

    content = []
    # Add the title and description
    content.append(
        Paragraph("File Search Algorithm Performance Report", styles["Title"])
    )
    content.append(
        Paragraph(
            "This report presents the performance of different file search algorithms with and without rereading the file on each query.",
            styles["BodyText"],
        )
    )

    data = [
        [
            "File Size",
            "REREAD_ON_QUERY",
            "Avg Response Time (seconds)",
            "Queries per Second",
        ]
    ]

    # Fill the table data with results
    for file_size, reread_on_query, avg_time, queries_per_second in results:
        data.append(
            [file_size, reread_on_query, f"{avg_time:.4f}", f"{queries_per_second:.2f}"]
        )

    # Create and style the table
    table = Table(data)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
            ]
        )
    )

    # Append the table to the content
    content.append(table)

    # Build the PDF
    doc.build(content)


if __name__ == "__main__":
    query = "25;0;23;16;0;19;3;0;"  # Example query
    file_sizes = [10000, 100000, 1000000]  # Example file sizes for testing
    max_queries_per_file = 100  # Number of queries for each test
    results = []

    for reread_on_query in [False, True]:
        # Update the server configuration for each test scenario
        update_config(reread_on_query)
        time.sleep(2)  # Allow the server to reload config

        for size in file_sizes:
            print(
                f"Testing with file size: {size} and REREAD_ON_QUERY={reread_on_query}"
            )
            avg_time, queries_per_second = run_queries(
                size, query, max_queries_per_file
            )
            results.append((size, reread_on_query, avg_time, queries_per_second))

    # Generate the report
    create_pdf_report(results)
    print("PDF generated as 'speed_report.pdf'.")
