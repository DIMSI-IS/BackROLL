"""The files of the installation: what keeps an installation from being broken by a second setup or by a recreated
container. They are read as text, they need neither Docker nor a shell."""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
COMPOSE = ROOT / "compose_project"
# In the container of the API the files of the installation are not there: these tests run in the CI and on the sources.
pytestmark = pytest.mark.skipif(not (COMPOSE / "source-me.sh").is_file(), reason="the files of the installation are not here")


def test_the_setup_refuses_to_overwrite_the_files_of_an_installation_that_exists():
    script = (COMPOSE / "source-me.sh").read_text(encoding="utf-8")
    # It checks the file of the mode and asks to type a word before overwriting it.
    assert '-e "@$backroll_mode.env"' in script
    assert 'response" != "overwrite"' in script
    assert "return 1" in script.split('"overwrite"')[1].split("esac")[0]


def test_the_secrets_have_a_key_apart_from_the_one_of_the_tokens():
    script = (COMPOSE / "source-me.sh").read_text(encoding="utf-8")
    template = (COMPOSE / "template.env").read_text(encoding="utf-8")
    assert "secrets_key=$(openssl rand -hex 32)" in script
    assert "export secrets_key" in script
    assert "SECRETS_KEY=$secrets_key" in template.splitlines()


def test_nginx_resolves_the_addresses_of_the_containers_at_each_request():
    conf = (ROOT / "src" / "server" / "containers.conf").read_text(encoding="utf-8")
    assert "resolver 127.0.0.11" in conf
    # A variable in proxy_pass: the name is resolved when the request comes, so a recreated container is found again.
    assert "proxy_pass $api_upstream;" in conf and "proxy_pass $front_upstream;" in conf
    assert "proxy_pass http://api" not in conf and "proxy_pass http://front" not in conf
