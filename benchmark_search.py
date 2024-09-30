import time
import subprocess
import os
import bisect
import pandas as pd
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet


# Search algorithms
def python_naive_search(file_path, query_string):
    start_time = time.time()
    with open(file_path, "r") as file:
        for line in file:
            if query_string in line.strip():
                return time.time() - start_time
    return time.time() - start_time


def python_set_search(file_path, query_string):
    start_time = time.time()
    with open(file_path, "r") as file:
        cached_lines = set(line.strip() for line in file)
    return (
        time.time() - start_time
        if query_string in cached_lines
        else time.time() - start_time
    )


def grep_search(file_path, query_string):
    start_time = time.time()
    result = subprocess.run(
        ["grep", "-Fxq", query_string, file_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return time.time() - start_time


def awk_search(file_path, query_string):
    start_time = time.time()
    result = subprocess.run(
        ["awk", f"/{query_string}/{{exit 0}}", file_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return time.time() - start_time


def binary_search(file_path, query_string):
    start_time = time.time()
    with open(file_path, "r") as file:
        lines = [line.strip() for line in file]
    lines.sort()
    index = bisect.bisect_left(lines, query_string)
    if index < len(lines) and lines[index] == query_string:
        return time.time() - start_time
    return time.time() - start_time


# Benchmarking function
def benchmark_search_methods(file_path, query_string):
    methods = {
        "Python Naive": python_naive_search,
        "Python Set": python_set_search,
        "Grep Search": grep_search,
        "Awk Search": awk_search,
        "Binary Search (sorted files)": binary_search,
    }

    results = {}
    for name, method in methods.items():
        exec_time = method(file_path, query_string)
        results[name] = exec_time
        print(f"{name}: {exec_time:.6f} seconds")

    return results


def generate_pdf_report(results, file_path):
    doc = SimpleDocTemplate(file_path, pagesize=letter)
    styles = getSampleStyleSheet()
    content = []

    content.append(
        Paragraph("File Search Algorithm Performance Report", styles["Title"])
    )
    content.append(
        Paragraph(
            "This report presents the performance of different file search algorithms.",
            styles["BodyText"],
        )
    )

    data = [["Algorithm", "Execution Time (seconds)"]]

    # Use .items() to unpack both key and value (algorithm name and execution time)
    for algo_name, exec_time in results.items():
        data.append([algo_name, f"{exec_time:.4f}"])

    table = Table(data)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), "grey"),
                ("TEXTCOLOR", (0, 0), (-1, 0), "white"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 1, "black"),
            ]
        )
    )

    content.append(table)
    doc.build(content)


# Plotting function
def plot_results(results, file_name):
    df = pd.DataFrame(results)
    df.plot(kind="bar")
    plt.title("File Search Algorithm Performance")
    plt.ylabel("Execution Time (seconds)")
    plt.savefig(file_name)
    plt.show()


def main():
    file_sizes = [
        "data_10k.txt",
        "data_50000.txt",
        "data_100000.txt",
        "data_250000.txt",
    ]
    query = "line_08699"
    results = {}

    for file_path in file_sizes:
        if os.path.isfile(file_path):
            print(f"\nBenchmarking for file: {file_path}")
            file_results = benchmark_search_methods(file_path, query)
            results[file_path] = file_results
        else:
            print(f"File not found: {file_path}")

    # Generate PDF report
    pdf_path = "search_algorithm_performance_report.pdf"
    for file_path, result in results.items():
        generate_pdf_report(result, pdf_path)

    # Generate plot
    plot_results(results, "search_performance.png")


if __name__ == "__main__":
    main()
