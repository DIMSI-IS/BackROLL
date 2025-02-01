import os
import subprocess
from subprocess import CalledProcessError


class ShellException(BaseException):
    def __init__(self, message, exit_code, stderr=None):
        super().__init__(message)
        self.exit_code = exit_code
        self.stderr = stderr


def os_system(command):
    print(f"[os_system] {command}")
    exit_status = os.system(command)
    exit_code = os.waitstatus_to_exitcode(exit_status)
    if exit_code != 0:
        print(f"[os_system] {exit_code=}")
        raise ShellException(f"[os_system] {exit_code=}", exit_code)


def os_popen(command):
    print(f"[os_popen] {command}")
    file = os.popen(command)
    result = file.read()

    exit_status = file.close()
    if exit_status is not None:
        exit_code = os.waitstatus_to_exitcode(exit_status)
        print(f"[os_popen] {exit_code=}")
        raise ShellException(f"[os_popen] {exit_code=}", exit_code)

    print(f"[os_popen] {result=}")
    return result


def subprocess_run(command):
    print(f"[subprocess_run] {command}")
    try:
        result = subprocess.run(
            command, capture_output=True, shell=True, check=True, text=True).stdout
        print(f"[subprocess_run] {result=}")
        return result
    except CalledProcessError as error:
        exit_code = error.returncode  # TODO Not always the right value…
        stderr = error.stderr
        print(f"[subprocess_run] {exit_code=}")
        print(f"[subprocess_run] {stderr=}")
        raise ShellException(
            f"[subprocess_run] {exit_code=} {stderr=}", exit_code, stderr)


def subprocess_popen(command):
    print(f"[subprocess_popen] {command}")
    process = subprocess.Popen(
        command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    while True:
        process.stdout.flush()
        output = process.stdout.readline()
        if output == '' and process.poll() is not None:
            break
        elif not output and process.poll() is not None:
            break
