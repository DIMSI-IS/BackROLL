from uuid import UUID


def ensure_uuid(uuid_like):
    return uuid_like if type(uuid_like) == UUID else UUID(uuid_like)


def make_path(*paths, directory=False):
    path = "/".join(map(lambda p: p.removesuffix("/"), paths))
    if directory:
        return f"{path}/"
    return path
