import json
import subprocess
import os

def run_command(command):
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
    if result.returncode != 0:
        print(f"Error executing command: {command}. Error was {result.stderr}")
        return None
    return result.stdout

def create_partition(device):
    command = f"echo -e 'n\np\n1\n\n\nw' | sudo fdisk {device}"
    return run_command(command)

def format_partition(partition_path):
    command = f"sudo mkfs.ext4 {partition_path}"
    return run_command(command)

def mount_partition(device, mount_point):
    if not os.path.exists(mount_point):
        os.makedirs(mount_point)

    command = f"sudo mount {device} {mount_point}"
    return run_command(command)

def set_directory_permissions(directory_path):
    command = f"sudo chmod 777 {directory_path}"
    return run_command(command)

def main():
    lsblk_output = run_command("lsblk -J")
    if not lsblk_output:
        return
    
    devices = json.loads(lsblk_output)
    
    volume_number = 0

    for device in devices["blockdevices"]:
        # Check if the device doesn't have any children (partitions)
        if not device.get("children"):
            print(f"Device {device['name']} does not have a partition. Creating one now.")
            create_partition(f"/dev/{device['name']}")

    # Check for partitions again after creating them
    lsblk_output = run_command("lsblk -J")
    devices = json.loads(lsblk_output)

    for device in devices["blockdevices"]:
        if device.get("children") and len(device.get("children")) == 1:
            format_partition(f"/dev/{device['children'][0]['name']}")
            volume_number += 1
            mount_point = f"/tmp/volume-{volume_number:02}"
            print(f"Mounting {device['children'][0]['name']} to {mount_point}")
            mount_partition(f"/dev/{device['children'][0]['name']}", mount_point)

            # Set directory permissions to 777
            set_directory_permissions(mount_point)
if __name__ == "__main__":
    main()
