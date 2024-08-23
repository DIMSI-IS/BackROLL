import subprocess

def run(script):
    print(f'[run] {script}')
    output = subprocess.run(script, shell=True, check=True, capture_output=True).stdout.decode('utf8').splitlines()
    for line in output:
        print(f'[run] {line}')
    return output
