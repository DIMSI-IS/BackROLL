import subprocess

def run(script):
    print(f'[run] {script}')
    return subprocess.run(script, shell=True, check=True, capture_output=True).stdout.decode('utf8').splitlines()
