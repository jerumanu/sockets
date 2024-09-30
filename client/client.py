import socket

def main():
    """
    A simple client program that connects to a server, sends a query,
    and receives a response.
    """
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(('localhost', 9997))

    query_string = "25;0;1;26;0;9;5;0;"  
    client.send(query_string.encode('utf-8'))

    response = client.recv(4096)
    print(response.decode('utf-8'))

    client.close()

if __name__ == "__main__":
    main()
