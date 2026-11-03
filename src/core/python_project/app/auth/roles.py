from enum import Enum


class Role(str, Enum):
    """Roles ordered from the least to the most privileged.

    - viewer: read only.
    - editor: viewer + create, update and delete resources, start backups and restores.
    - admin: editor + manage users.
    """
    VIEWER = "viewer"
    EDITOR = "editor"
    ADMIN = "admin"

    @property
    def rank(self) -> int:
        return list(Role).index(self)
