import os
import subprocess
from subprocess import CalledProcessError

from app.logging import logged


class ShellException(Exception):
    def __init__(self, exit_code, stderr=None):
        super().__init__(f"{exit_code=} {stderr}")
        self.exit_code = exit_code
        self.stderr = stderr


@logged(bounds=False)
def os_system(command, logger):
    logger.info(command)
    exit_status = os.system(command)
    exit_code = os.waitstatus_to_exitcode(exit_status)
    if exit_code != 0:
        logger.info(f"{exit_code=}")
        raise ShellException(exit_code)


@logged(bounds=False)
def os_popen(command, logger):
    logger.info(command)
    file = os.popen(command)
    result = file.read()

    exit_status = file.close()
    if exit_status is not None:
        exit_code = os.waitstatus_to_exitcode(exit_status)
        logger.info(f"{exit_code=}")
        raise ShellException(exit_code)

    logger.info(result)
    return result


@logged(bounds=False)
def subprocess_run(command, logger):
    logger.info(command)
    try:
        stdout = subprocess.run(
            command, capture_output=True, shell=True, check=True, text=True).stdout
        logger.info(stdout)
        return stdout
    except CalledProcessError as error:
        exit_code = error.returncode  # TODO Not always the right value…
        stderr = error.stderr
        logger.info(f"{exit_code=}")
        logger.info(stderr)
        raise ShellException(exit_code, stderr)


@logged(bounds=False)
def subprocess_popen(command, logger):
    logger.info(command)
    process = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, text=True)
    (stdout, stderr) = process.communicate()

    exit_code = process.returncode
    if exit_code != 0:
        logger.info(f"{exit_code=}")
        logger.info(stderr)
        raise ShellException(exit_code, stderr)

    logger.info(stdout)
    return stdout
