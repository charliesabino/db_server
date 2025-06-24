from typing import Any
import socket

class Database:
    def __init__(self):
        self.kv_store = {}
    
    def get(self, key: str) -> Any:
        return self.kv_store.get(key)
    
    def set(self, key: str, value: Any) -> None:
        self.kv_store[key] = value

class Server:
    def __init__(self):
        self.db = Database()
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind(("127.0.0.1", 4000))
        self.server.listen()
    
    def accept(self):
        return self.server.accept()
    
    def handle_client(self, client_socket: socket.socket):
        # Read the full request
        request_data = b""
        while b"\r\n\r\n" not in request_data:
            chunk = client_socket.recv(1024)
            if not chunk:
                break
            request_data += chunk

        self.handle_request(request_data)
        
    def handle_request(self, request_data: bytes):
        
        

    def close(self):
        self.server.close()

def main():
    server = Server()

    # could employ threads / asyncio / etc. here to handle multiple clients; omitted for simplicity
    while True:
        client_socket, client_address = server.accept()
        server.handle_client(client_socket)
        client_socket.close()

if __name__ == "__main__":
    main()
