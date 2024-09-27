from uuid import UUID


def ensure_uuid(uuid_like):
    return uuid_like if type(uuid_like) == UUID else UUID(uuid_like)


def make_path(*paths, rooted=None, directory=None):
    rooted = paths[0].startswith("/") if rooted is None else rooted
    directory = paths[-1].endswith("/") if directory is None else directory
    path = "/".join(map(lambda p: p.removeprefix("/").removesuffix("/"), paths))
    if rooted:
        path = f"/{path}"
    if directory:
        path = f"{path}/"
    print(f"[make_path] {path}")
    return path
