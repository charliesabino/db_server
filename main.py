from typing import Optional
import socket

class Database:
    def __init__(self):
        self.kv_store = {}

    def get(self, key: str) -> Optional[str]:
        return self.kv_store.get(key)

    def set(self, key: str, value: str) -> None:
        self.kv_store[key] = value

class Server:
    def __init__(self):
        self.db = Database()
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # socket reuse
        self.server.bind(("127.0.0.1", 4000))
        self.server.listen()
        print("Server listening on http://127.0.0.1:4000")

    def accept(self):
        return self.server.accept()

    def handle_client(self, client_socket: socket.socket):
        try:
            request_data = b""

            # this is inefficient but KISS
            while b"\r\n\r\n" not in request_data:
                chunk = client_socket.recv(1024)
                if not chunk:
                    break
                request_data += chunk

            if request_data:
                response_body = self.handle_request(request_data)
                self.send_response(client_socket, response_body)
        except Exception as e:
            print(f"Error handling client: {e}")
            self.send_response(client_socket, f"Error: {str(e)}")

    def parse_request(self, request_data: bytes):
        request_str = request_data.decode('utf-8')
        lines = request_str.split('\r\n')
        # first line is the request line
        request_line = lines[0]

        # looks like "GET /set?key=value HTTP/1.1" or "GET /get?key=somekey HTTP/1.1"
        _, full_path, _ = request_line.split(' ')
        print(f"path: {full_path}")

        # Handle missing query string
        if '?' not in full_path:
            return full_path, "", ""

        path, query_string = full_path.split('?', 1)

        # Handle missing = in query string
        if '=' not in query_string:
            return path, query_string, ""

        param1, param2 = query_string.split("=", 1)  # Added maxsplit=1 for values with =

        return path, param1, param2

    def handle_request(self, request_data: bytes) -> str:
        # Parse the request
        operation, param1, param2 = self.parse_request(request_data)

        # could use dispatch table here, but this is fine for now
        if operation == '/set':
            if not param1 or not param2:
                response_body = "Error: /set requires key=value format"
            else:
                self.db.set(param1, param2)
                response_body = f"Successfully set {param1} to {param2}"
        elif operation == '/get':
            if not param2:
                response_body = "Error: /get requires key=somekey format"
            else:
                value = self.db.get(param2)
                if value is None:
                    response_body = f"Database does not contain key {param2}"
                else:
                    response_body = value
        else:
            response_body = "Unknown operation"

        return response_body

    def send_response(self, client_socket: socket.socket, body: str) -> str:
        response = "HTTP/1.1 200 OK\r\n"
        response += "Content-Type: text/plain\r\n"
        response += f"Content-Length: {len(body)}\r\n"
        response += "Connection: close\r\n"
        response += "\r\n"
        response += body

        client_socket.sendall(response.encode('utf-8'))

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
