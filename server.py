from typing import Any, Optional, Tuple
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
            # Read the full request
            request_data = b""

            # this is inefficient but KISS
            while b"\r\n\r\n" not in request_data:
                chunk = client_socket.recv(1024)
                if not chunk:
                    break
                request_data += chunk

            if request_data:
                status_code, response_body = self.handle_request(request_data)
                self.send_response(client_socket, status_code, response_body)
            else:
                self.send_response(client_socket, 400, "Bad Request: Empty request")
        except Exception as e:
            print(f"Error handling client: {e}")
            self.send_response(client_socket, 500, f"Internal Server Error: {str(e)}")

    def parse_request(self, request_data: bytes) -> Tuple[str, str, str, str]:
        request_str = request_data.decode('utf-8')
        lines = request_str.split('\r\n')
        
        if not lines:
            raise ValueError("Empty request")
            
        # first line is the request line
        request_line = lines[0]

        # looks like "GET /set?key=value HTTP/1.1"
        parts = request_line.split(' ')
        if len(parts) != 3:
            raise ValueError("Malformed request line")
            
        method, full_path, _ = parts
        print(f"method: {method}, path: {full_path}")

        # Handle missing query string
        if '?' not in full_path:
            return method, full_path, "", ""
        
        path, query_string = full_path.split('?', 1)
        
        # Handle missing = in query string
        if '=' not in query_string:
            return method, path, query_string, ""
        
        param1, param2 = query_string.split("=", 1)  # maxsplit=1 for values with =

        return method, path, param1, param2

    def handle_request(self, request_data: bytes) -> Tuple[int, str]:
        try:
            # Parse the request
            method, operation, param1, param2 = self.parse_request(request_data)

            # Check HTTP method
            if method != 'GET':
                return 405, f"Method Not Allowed: {method}. Only GET is supported"

            # Route based on path
            if operation == '/set':
                if not param1 or not param2:
                    return 400, "Bad Request: /set requires key=value format"
                else:
                    self.db.set(param1, param2)
                    return 200, f"Successfully set {param1} to {param2}"
            elif operation == '/get':
                if not param2:
                    return 400, "Bad Request: /get requires key=somekey format"
                else:
                    value = self.db.get(param2)
                    if value is None:
                        return 404, f"Not Found: Database does not contain key {param2}"
                    else:
                        return 200, value
            else:
                return 404, f"Not Found: Unknown path {operation}"

        except ValueError as e:
            return 400, f"Bad Request: {str(e)}"
        except Exception as e:
            return 500, f"Internal Server Error: {str(e)}"

    def send_response(self, client_socket: socket.socket, status_code: int, body: str) -> None:
        status_text = {
            200: "OK",
            400: "Bad Request",
            404: "Not Found",
            405: "Method Not Allowed",
            500: "Internal Server Error"
        }.get(status_code, "Unknown")

        response = f"HTTP/1.1 {status_code} {status_text}\r\n"
        response += "Content-Type: text/plain\r\n"
        response += f"Content-Length: {len(body)}\r\n"
        response += "Connection: close\r\n"
        response += "\r\n"
        response += body

        try:
            client_socket.sendall(response.encode('utf-8'))
        except Exception as e:
            print(f"Error sending response: {e}")

    def close(self):
        self.server.close()

def main():
    server = Server()

    try:
        # could employ threads / asyncio / etc. here to handle multiple clients; omitted for simplicity
        while True:
            client_socket, client_address = server.accept()
            print(f"Connection from {client_address}")
            server.handle_client(client_socket)
            client_socket.close()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.close()

if __name__ == "__main__":
    main()
