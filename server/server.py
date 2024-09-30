import bisect
import socket
import threading
import time
import logging
import ssl
from typing import Optional, Set, Tuple


logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Set maximum buffer size to prevent overflow
BUFFER_SIZE = 1024
# Set a limit on the query string length
MAX_STRING_LENGTH = 256


def get_config_options(
    config_file: str,
) -> Tuple[Optional[str], bool, bool, Optional[str], Optional[str]]:
    """
    Reads configuration options from the specified file.

    Arguments:

        config_file (str): The file location of the configuration.

    Returns:

        tuple: Contains a tuple with the following in sequence.

            -linux_path (str or None): The linux directory path.

            -reread_on_query (bool): Do reread the configuration file with each query.

            -ssl_enabled (bool): Is SSL enabled.

            -certfile (str or None): Path to the ssl certificate file.

            -keyfile (str or None): Path to the ssl key file.

    """

    linux_path = None
    reread_on_query = False
    ssl_enabled = False
    certfile = None
    keyfile = None

    try:
        with open(config_file, "r") as file:
            for line in file:
                if line.startswith("linuxpath="):
                    linux_path = line.split("=", 1)[1].strip()
                elif line.startswith("REREAD_ON_QUERY="):
                    reread_on_query = line.split("=", 1)[1].strip().lower() == "true"
                elif line.startswith("SSL_ENABLED="):
                    ssl_enabled = line.split("=", 1)[1].strip().lower() == "true"
                elif line.startswith("CERT_FILE="):
                    certfile = line.split("=", 1)[1].strip()
                elif line.startswith("KEY_FILE="):
                    keyfile = line.split("=", 1)[1].strip()
    except FileNotFoundError:
        logging.error(f"Configuration file '{config_file}' not found.")
    except Exception as e:
        logging.error(f"Error while reading the configuration file: {e}")

    return linux_path, reread_on_query, ssl_enabled, certfile, keyfile


def load_file_to_cache(file_path: str) -> Set[str]:
    """Accumulates the content of the specified file into a set.

    Args:
        file_path (str): Name of the file to load..

    Returns:
        set:Set of file lines
    """

    cached_lines = set()

    try:
        with open(file_path, "r") as file:
            for line in file:
                cached_lines.add(line.strip())
    except FileNotFoundError:
        logging.error(f"File '{file_path}' is not found.")
    except Exception as e:
        logging.error(f"There was an error while reading the file: {e}")

    return cached_lines


def binary_search_in_file(
    file_path: str,
    query_string: str,
    reread_on_query: bool,
    cached_lines: Optional[Set[str]],
) -> Tuple[bool, float]:
    """Performs a binary search on a file for a given query string.

    Args:
        file_path (basestring): The path to the file to search.

        query_string: A str Query string to search against.

        reread_on_query (bool): Controls whether the file is to be reread on each query.

        cached_lines (set): lines of the file in set or none

    Returns:
        type tuple: a type tuple containing:
            - found (bool): a boolean indicating if the query string was found.

            exec_time (float): The time took to execute (seconds).
            - found (bool): a boolean indicating if the query string was found.
            -exec_time (float): The time took to execute (seconds).
    """

    start_time = time.time()

    if reread_on_query:
        with open(file_path, "r") as file:
            lines = [line.strip() for line in file]
        lines.sort()
        index = bisect.bisect_left(lines, query_string)
        found = index < len(lines) and lines[index] == query_string
    else:
        found = query_string in cached_lines

    exec_time = time.time() - start_time
    return found, exec_time


def handle_client(
    client_socket: socket.socket,
    file_path: str,
    reread_on_query: bool,
    cached_lines: Optional[Set[str]],
) -> None:
    """Handles a client connection, processing search queries and sending responses.

    Args:
        client_socket (socket. socket): The client socket.

        file_path (str): Save the path as file_path.

        reread_on_query (bool, default=False): Whether to reread file every query.

        cached_lines (set): A set of lines from file.
    """

    try:
        while True:
            request = client_socket.recv(BUFFER_SIZE)
            if not request:
                break

            # Strip null bytes and sanitize input
            query_string = request.replace(b"\x00", b"").decode("utf-8").strip()
            print(len(query_string))
            # Ensure query string is within safe limits
            if len(query_string) > MAX_STRING_LENGTH:
                logging.error(
                    f"Query string too long: {query_string[:50]}... (truncated)"
                )
                client_socket.send(b"ERROR: Query string too long.\n")
                continue

            client_ip = client_socket.getpeername()[0]
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            logging.debug(
                f"Received search query '{query_string}' from IP {client_ip} at {timestamp}"
            )

            result, exec_time = binary_search_in_file(
                file_path, query_string, reread_on_query, cached_lines
            )

            if result:
                response = f"STRING EXISTS (Execution Time: {exec_time:.4f} seconds)\n"
            else:
                response = (
                    f"STRING NOT FOUND (Execution Time: {exec_time:.4f} seconds)\n"
                )

            client_socket.send(response.encode("utf-8"))

            logging.debug(
                f"Sent response to IP {client_ip}: {response.strip()} (Execution Time: {exec_time:.4f} seconds)"
            )
    except ConnectionResetError:
        logging.debug("Connection closed by the client.")
    finally:
        client_socket.close()


def start_server(config_file: str, host: str = "0.0.0.0", port: int = 9997) -> None:
    """Starts a server to handle client search queries on a specified file.

    Args:
        config_file (str): Configuration file path.
        host (str, optional): The hostname/IP address where Tornado should bind() to. Defaults to '0.0.0.0' (all interfaces)
        port (int, optional) – Port number to listen on. Defaults to 9997.


    Raises:
        Re: If path to the file cannot be found in configuration, or if SSL enabled but certificate/key file not present (in print)
    """

    # Read configuration options
    file_path, reread_on_query, ssl_enabled, certfile, keyfile = get_config_options(
        config_file
    )

    if file_path:
        logging.info(f"Path found in config: {file_path}")
        logging.info(f"REREAD_ON_QUERY set to: {reread_on_query}")
    else:
        logging.error(
            "Path not found in config. Server will still start, but file path is unavailable."
        )
        return

    # Initialize cached lines if not rereading on query
    cached_lines = None
    if not reread_on_query:
        cached_lines = load_file_to_cache(file_path)
        logging.info("File content cached for future queries (REREAD_ON_QUERY=False)")

    # Create server socket
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # Allow port reuse
    server.bind((host, port))

    # Enable SSL if configured
    if ssl_enabled:
        if not certfile or not keyfile:
            logging.error("SSL is enabled, but certificate or key file is missing.")
            return

        logging.info("SSL enabled. Wrapping socket with SSL.")
        server = ssl.wrap_socket(
            server, certfile=certfile, keyfile=keyfile, server_side=True
        )

    # Start listening for connections
    server.listen(5)  # Listen for a maximum of 5 pending connections
    logging.info(f"Listening on {host}:{port}")

    # accept connections and process them in seperate threads
    while True:
        client_socket, addr = server.accept()
        logging.info(f"Accepted connection from {addr}")
        client_handler = threading.Thread(
            target=handle_client,
            args=(client_socket, file_path, reread_on_query, cached_lines),
        )
        client_handler.daemon = True  # Set thread as daemon to allow program exit
        client_handler.start()


if __name__ == "__main__":
    config_file_path = "server_config.cfg"
    start_server(config_file_path)
