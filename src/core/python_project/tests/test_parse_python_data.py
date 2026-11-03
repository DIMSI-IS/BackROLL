"""The arguments of the tasks come from Flower as text (the `repr` of the Python values), sometimes cut short.

`parse_python_data` repairs a text that is not valid by removing characters, then reads it. It used `eval`: a text
that is cut inside a string, with the name of a machine in it, made the repair remove the quote that opens the
string, and the name was then run as Python code. The text is now only read as data (`ast.literal_eval`).
"""

import os

import pytest

os.environ.setdefault("JWT_SECRET", "x" * 40)

from app.patch import parse_python_data  # noqa: E402

VM = {"name": "web-01", "uuid": "11111111-1111-1111-1111-111111111111", "state": "Running", "id": 3,
      "storage": [{"device": "vda", "source": "/mnt/pool/a.qcow2"}], "ok": True, "backing": None}


def test_the_arguments_of_a_task_are_read_as_data():
    assert parse_python_data(repr((VM,))) == [VM]


def test_a_list_a_number_and_a_string_are_read_too():
    assert parse_python_data("[1, 2.5, 'a', None, True]") == [1, 2.5, "a", None, True]
    assert parse_python_data("'just text'") == "just text"


def test_a_text_that_is_not_data_is_refused_not_run(tmp_path):
    marker = tmp_path / "ran"
    with pytest.raises(ValueError):
        parse_python_data(f"open({str(marker)!r}, 'w').write('x')")
    assert not marker.exists()


def test_a_name_in_a_text_cut_short_is_never_run_as_code(tmp_path):
    """A virtual machine named with Python code: when the text is cut inside its name, the repair that removes the
    opening quote used to leave the name outside of a string, and `eval` ran it."""
    marker = tmp_path / "ran"
    payload = f"'+open({str(marker)!r}, 'w').write('x')+'"
    text = repr((dict(VM, name=payload),))
    # The text is cut at every length, as Flower does with long arguments.
    for length in range(1, len(text)):
        try:
            parse_python_data(text[:length])
        except ValueError:
            pass
    assert not marker.exists(), "the name of a machine was run as code"


def test_a_text_that_is_cut_short_is_repaired_when_it_can_be_or_refused():
    text = repr((VM,))
    for length in range(1, len(text)):
        try:
            result = parse_python_data(text[:length])
        except ValueError:
            continue
        # Whatever it gives back is plain data that can be sent as JSON.
        assert result is None or isinstance(result, (list, dict, str, int, float, bool))
