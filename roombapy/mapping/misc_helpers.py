import os

def get_mapper_asset(path: str, resource: str):
    if path is None or path.isspace() or path == "":
        return resource
    if path.startswith("{PKG}"):
        return os.path.normpath(os.path.join(os.path.dirname(__file__), path.replace("{PKG}",".."), resource))
    else:
        return os.path.normpath(os.path.join(path, resource))
