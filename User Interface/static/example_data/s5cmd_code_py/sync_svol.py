import subprocess

def run_scripts():
    # Paths to the scripts
    src_script = 'src_sync_svol.py'
    dest_script = 'dest_sync_svol.py'

    # Starting both scripts simultaneously
    processes = []
    processes.append(subprocess.Popen(['python', src_script]))
    processes.append(subprocess.Popen(['python', dest_script]))
    
    # Wait for both scripts to complete
    for proc in processes:
        proc.wait()

if __name__ == '__main__':
    run_scripts()