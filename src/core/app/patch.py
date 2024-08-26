from uuid import UUID

def ensure_uuid(uuid_like):
    return uuid_like if type(uuid_like) == UUID else UUID(uuid_like)
