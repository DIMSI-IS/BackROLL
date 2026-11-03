"""The groups of archives: the retention is applied to each of them apart."""

import os

import pytest

os.environ.setdefault("JWT_SECRET", "x" * 40)

from app import archives  # noqa: E402


@pytest.mark.parametrize("name,group", [
    ("vda_7ec628cb-9b70_1792276772", "vda_7ec628cb-9b70"),
    ("files_etc_1792268246", "files_etc"),
    ("files_var-www_1792268246", "files_var-www"),
    ("data_1_disk_1792268246", "data_1_disk"),
    ("template", None),
    ("vda_no-timestamp", None),
    ("_12345", None),
])
def test_the_group_is_the_name_without_the_timestamp(name, group):
    assert archives.group_of(name) == group


def test_two_folders_of_a_backup_are_two_groups():
    found = archives.groups([{"name": "files_etc_5"}, {"name": "files_var-www_5"}, {"name": "files_etc_9"},
                             {"name": "vda_x_5"}, {"name": "vdb_y_5"}])
    assert found == ["files_etc", "files_var-www", "vda_x", "vdb_y"]


def test_the_characters_of_a_glob_are_escaped():
    assert archives.escape_glob("a*b?c[d]") == "a[*]b[?]c[[]d]"
    assert archives.glob_of("data[1]") == "data[[]1]_[0-9]*"


def test_a_disk_does_not_match_the_disk_that_starts_like_it():
    import fnmatch
    pattern = archives.glob_of("DATA-1_disk")
    assert fnmatch.fnmatchcase("DATA-1_disk_123", pattern)
    assert not fnmatch.fnmatchcase("DATA-10_disk_123", pattern)
