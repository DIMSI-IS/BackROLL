import os
import subprocess


def os_system(command, check=True):
    print(f"[os_system] {command}")
    return_code = os.system(command)

    if not check:
        return return_code

    if return_code != 0:
        raise RuntimeError(f"[os_system] {return_code=}")


def os_popen(command):
    print(f"[os_popen] {command}")
    return os.popen(command).read()


def subprocess_run(command, check=True):
    print(f"[subprocess_run] {command}")
    return subprocess.run(command.split(), text=True, capture_output=True, check=check)


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
