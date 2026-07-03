import json
import yaml

from kazoo.exceptions import NoNodeError, NotEmptyError


class Node:
    def __init__(self, name: str, value: dict | None = None, children: dict | None = None):
        self.name = name
        self.value = value
        self.children = children if children else {}


def print_node(node: Node, indentation=0):
    """Convenience function to print a node structure."""
    print(" "*indentation + f"Node(name={node.name}", end="")
    print(f", value={node.value}" if node.value else "", end="")
    if node.children:
        print(", ", end="")
        print()
        print(" "*(indentation+4) + f"children=")
        for child_name, child_value in node.children.items():
            print_node(child_value, indentation=8+indentation)
        print(" "*indentation + ")")
    else:
        print(")")


# Fake ZK KazooClient
class FakeZK:
    def __init__(self, hosts: list[str], root: Node):
        self.hosts = hosts  # Preserve KazooClient api.
        self.root = root

    def _get_zk_node(self, path):
        parts = path.strip("/").split("/")
        node = self.root
        try:
            for part in parts:
                node = node.children[part]
            if node.value is not None:
                return json.dumps(node.value).encode("utf-8"), list(node.children.keys())
            return "".encode("utf-8"), list(node.children.keys())
        except KeyError:
            raise NoNodeError

    def ensure_path(self, path):
        parts = path.strip("/").split("/")
        node = self.root

        for part in parts:
            if part not in node.children:
                node.children[part] = Node(name=part)
            node = node.children[part]

    def exists(self, path):
        parts = path.strip("/").split("/")
        node = self.root
        try:
            for part in parts:
                node = node.children[part]
        except KeyError:
            return False
        return True

    def create(self, path: str, data: bytes, makepath: bool = False):
        if not self.exists(path) and not makepath:
            raise NoNodeError("Node does not exist!")
        self.ensure_path(path=path)
        self.set(path, data)

    def get(self, path):
        return self._get_zk_node(path)

    def get_children(self, path):
        return self._get_zk_node(path)[1]

    def set(self, path: str, data: bytes, version: int = -1):
        if not isinstance(data, bytes):
            raise TypeError()
        parts = path.strip("/").split("/")
        filename = parts[-1]
        node = self.root

        try:
            if filename.endswith(".json"):
                processed_data = json.loads(data.decode("utf-8"))
            elif filename.endswith((".yml", ".yaml")):
                processed_data = yaml.safe_load(data.decode("utf-8"))
            else:
                raise Exception(f"Unsupported file type: {filename}")
        except (json.JSONDecodeError, yaml.YAMLError, UnicodeDecodeError):
            processed_data = None
            pass  # zookeeper saves data even if cant decode

        try:
            for part in parts[:-1]:
                if part not in node.children:
                    node.children[part] = Node(name=part)
                node = node.children[part]
            node.children[filename] = Node(name=filename, value=processed_data)
        except KeyError:
            raise NoNodeError

    def delete(self, path: str, recursive: bool = False):
        # FIXME: implement recursive delete.
        parts = path.strip("/").split("/")
        filename = parts[-1]
        node = self.root

        try:
            for part in parts[:-1]:
                node = node.children[part]

            if len(node.children[filename].children) > 0:
                raise NotEmptyError
            del node.children[filename]
        except KeyError:
            raise NoNodeError

    def start(self):
        pass

    def stop(self):
        pass

    def close(self):
        pass
