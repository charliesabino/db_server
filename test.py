import pytest
import socket
import threading
import time
import requests
from typing import Optional

from server import Server, Database


class TestDatabase:
    def test_set_and_get(self):
        db = Database()
        db.set("key1", "value1")
        assert db.get("key1") == "value1"
    
    def test_get_nonexistent_key(self):
        db = Database()
        assert db.get("nonexistent") is None
    
    def test_overwrite_key(self):
        db = Database()
        db.set("key1", "value1")
        db.set("key1", "value2")
        assert db.get("key1") == "value2"
    
    def test_multiple_keys(self):
        db = Database()
        db.set("key1", "value1")
        db.set("key2", "value2")
        db.set("key3", "value3")
        
        assert db.get("key1") == "value1"
        assert db.get("key2") == "value2"
        assert db.get("key3") == "value3"


class ServerTestHelper:
    def __init__(self, port: int = 4001):
        self.port = port
        self.server = Server(port)
        self.thread = None
        self.base_url = f"http://127.0.0.1:{port}"
    
    def start(self):
        def run_server():
            while True:
                try:
                    client_socket, client_address = self.server.accept()
                    self.server.handle_client(client_socket)
                    client_socket.close()
                except OSError:
                    break
        
        self.thread = threading.Thread(target=run_server, daemon=True)
        self.thread.start()
        
        time.sleep(0.1)
        
    def stop(self):
        if self.server:
            self.server.close()
        if self.thread:
            self.thread.join(timeout=1)


@pytest.fixture
def server():
    helper = ServerTestHelper()
    helper.start()
    yield helper
    helper.stop()


class TestServerHTTP:
    def test_set_and_get_basic(self, server):
        response = requests.get(f"{server.base_url}/set?key1=value1")
        assert response.status_code == 200
        assert "Successfully set key1 to value1" in response.text
        
        response = requests.get(f"{server.base_url}/get?key=key1")
        assert response.status_code == 200
        assert response.text == "value1"
    
    def test_get_nonexistent_key(self, server):
        response = requests.get(f"{server.base_url}/get?key=nonexistent")
        assert response.status_code == 404
        assert "Database does not contain key nonexistent" in response.text
    
    def test_set_without_value(self, server):
        response = requests.get(f"{server.base_url}/set?key=")
        assert response.status_code == 400
        assert "Bad Request" in response.text
        assert "key=value format" in response.text
    
    def test_set_without_parameters(self, server):
        response = requests.get(f"{server.base_url}/set")
        assert response.status_code == 400
        assert "Bad Request" in response.text
    
    def test_get_without_key_parameter(self, server):
        response = requests.get(f"{server.base_url}/get")
        assert response.status_code == 400
        assert "Bad Request" in response.text
        assert "key=somekey format" in response.text
    
    def test_unknown_path(self, server):
        response = requests.get(f"{server.base_url}/unknown")
        assert response.status_code == 404
        assert "Not Found: Unknown path /unknown" in response.text
    
    def test_post_method_not_allowed(self, server):
        response = requests.post(f"{server.base_url}/set?key=value")
        assert response.status_code == 405
        assert "Method Not Allowed" in response.text
        assert "Only GET is supported" in response.text
    
    def test_multiple_sets_and_gets(self, server):
        test_data = {
            "name": "John",
            "age": "30",
            "city": "Chicago"
        }
        
        for key, value in test_data.items():
            response = requests.get(f"{server.base_url}/set?{key}={value}")
            assert response.status_code == 200
        
        for key, expected_value in test_data.items():
            response = requests.get(f"{server.base_url}/get?key={key}")
            assert response.status_code == 200
            assert response.text == expected_value
    
    def test_overwrite_value(self, server):
        response = requests.get(f"{server.base_url}/set?key1=initial")
        assert response.status_code == 200
        
        response = requests.get(f"{server.base_url}/set?key1=updated")
        assert response.status_code == 200
        
        response = requests.get(f"{server.base_url}/get?key=key1")
        assert response.status_code == 200
        assert response.text == "updated"
    
    def test_special_characters_in_values(self, server):
        test_cases = [
            ("space", "hello world", "hello%20world"),
            ("special", "a&b=c", "a%26b%3Dc"),
            ("unicode", "café", "caf%C3%A9"),
        ]
        
        for key, expected, encoded in test_cases:
            response = requests.get(f"{server.base_url}/set?{key}={encoded}")
            assert response.status_code == 200
            
            response = requests.get(f"{server.base_url}/get?key={key}")
            assert response.status_code == 200
            assert response.text == encoded
    
    def test_empty_value(self, server):
        response = requests.get(f"{server.base_url}/set?key=")
        assert response.status_code == 400
    
    def test_concurrent_requests(self, server):
        import concurrent.futures
        
        def make_request(i):
            response = requests.get(f"{server.base_url}/set?key{i}=value{i}")
            assert response.status_code == 200
            
            response = requests.get(f"{server.base_url}/get?key=key{i}")
            assert response.status_code == 200
            assert response.text == f"value{i}"
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request, i) for i in range(10)]
            for future in concurrent.futures.as_completed(futures):
                future.result()


class TestServerParsing:
    def test_parse_valid_set_request(self):
        server = Server()
        server.close()
        
        request = b"GET /set?key=value HTTP/1.1\r\nHost: localhost\r\n\r\n"
        method, path, param1, param2 = server.parse_request(request)
        
        assert method == "GET"
        assert path == "/set"
        assert param1 == "key"
        assert param2 == "value"
    
    def test_parse_valid_get_request(self):
        server = Server()
        server.close()
        
        request = b"GET /get?key=somekey HTTP/1.1\r\nHost: localhost\r\n\r\n"
        method, path, param1, param2 = server.parse_request(request)
        
        assert method == "GET"
        assert path == "/get"
        assert param1 == "key"
        assert param2 == "somekey"
    
    def test_parse_request_with_equals_in_value(self):
        server = Server()
        server.close()
        
        request = b"GET /set?key=a=b=c HTTP/1.1\r\nHost: localhost\r\n\r\n"
        method, path, param1, param2 = server.parse_request(request)
        
        assert method == "GET"
        assert path == "/set"
        assert param1 == "key"
        assert param2 == "a=b=c"
    
    def test_parse_request_without_query(self):
        server = Server()
        server.close()
        
        request = b"GET /set HTTP/1.1\r\nHost: localhost\r\n\r\n"
        method, path, param1, param2 = server.parse_request(request)
        
        assert method == "GET"
        assert path == "/set"
        assert param1 == ""
        assert param2 == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])