from typing import Any

class Database:
    def __init__(self):
        self.kv_store = {}
    
    def get(self, key: str) -> Any:
        return self.kv_store.get(key)
    
    def set(self, key: str, value: Any) -> None:
        self.kv_store[key] = value


def main():
    db = Database()

if __name__ == "__main__":
    main()
