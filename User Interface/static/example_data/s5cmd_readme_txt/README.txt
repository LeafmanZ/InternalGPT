About:

The text describes a set of requirements and setup instructions for a data transfer application or script, specifically tailored for the Linux operating system on AMD64 architecture. 
The application is developed in Go and Python, and it utilizes a tool called s5cmd for interacting with Amazon S3 services.

The preference for custom s5cmd scripts over the standard s5cmd stems from the latter's limitations, particularly in robust sync features. 
While standard s5cmd excels in creating concurrent copy commands for efficient data transfer, it falls short in preventing redundant data transfer. 
This issue becomes evident in complex tasks, such as performing a dual sync from an S3 Snowball to local storage and then to another S3 bucket. 
Such a limitation was highlighted during a power outage at the forward edge, where the native s5cmd sync failed to transfer data from the archiver to the snowball, 
a problem that was resolved using the custom sync script.

The custom scripts offer enhanced capabilities, including dual sync with checksum verification, support for multiple volume transfers to improve read/write speeds, and avoidance of data transfer bottlenecks. 
Additionally, they maintain a detailed ledger to monitor data at every transfer stage. 
A key advantage of these scripts is their compatibility with Versa SD-WAN, enabling data transfer via this network, a functionality absent in the native s5cmd.

=====================================================================================================================================================================================

Requirements:

    linux/amd64
    go version = 1.21.1
    s5cmd version = 2.2.2
    python3 version >= 3.9.0

=====================================================================================================================================================================================

Set up instructions (Applicable if prerequisites aren't installed):

    Navigate to this folder:
    cd path/to/this/transfer_v5
    Ensure that you are in the correct directory.

    Part 1: Installing GOlang

        If the file `go1.21.1.linux-amd64.tar.gz` is not present and internet access is available,
        you can obtain the file by executing the following command:
            wget https://go.dev/dl/go1.21.3.linux-amd64.tar.gz

        Execute the following commands in sequence:
            sudo tar -C /usr/local -xzf go1.21.3.linux-amd64.tar.gz
            echo "export PATH=$PATH:/usr/local/go/bin" >> ~/.profile
            source ~/.profile
            go version

        Upon successful execution, you should receive an output similar to:
            go version go1.21.3 linux/amd64

    Part 2: Installing s5cmd

        If the file `s5cmd_2.2.2_Linux-64bit.tar.gz` is not present and internet access is available,
        you can obtain the file by executing the following command:
            wget https://github.com/peak/s5cmd/releases/download/v2.2.2/s5cmd_2.2.2_Linux-64bit.tar.gz

        Execute the following commands in sequence:
            tar -xzf s5cmd_2.2.2_Linux-64bit.tar.gz
            chmod +x s5cmd
            ./s5cmd

        After executing, you'll observe an output displaying various s5cmd commands along with their usage guidelines.
        
    Part 3: Installing Python with Anaconda

        To install the latest version of Python, follow these steps:
            cd path/to/this/transfer_v5/conda
            bash Anaconda3-2023.09-0-Linux-x86_64.sh
            
        Follow the on-screen instructions during the installation process, pressing 'enter' and agreeing ('yes') when prompted.

        To verify that anaconda has been installed successfully, open a new terminal and run:
            conda
            
        After executing, you should see the conda help information displayed.

        It's advisable to have separate Python environments for different projects. Set up a new environment by running:        
            conda create --name s5cmd01 --clone base
            conda activate s5cmd01
        
        Install additional dependencies necessary for your project (with s5cmd01 activated):
            pip install s3transfer-0.6.2-py3-none-any.whl
            pip install boto3-1.26.69-py3-none-any.whl

        Ensure that you activate the s5cmd01 environment whenever you need to run Python scripts located in path/to/this/transfer_v5/
        Remember, activating the correct environment is crucial before running your Python scripts to ensure that all dependencies are available and configured properly.


=====================================================================================================================================================================================

Usage:

    Navigate to this folder:
    cd path/to/this/transfer_v5
    Ensure that you are in the correct directory.

    Part 1: Reset environment
        
        Execute this command solely on the initial run or when a complete reset is necessary, resulting in a re-transfer of all data.
    
        We need to refresh the environment by removing previous run data and details. 
        Subsequently, establish our volumes if distributing data across multiple concurrent volumes.
        
        Execute the following commands in sequence (if you are using anaconda use python instead of python3):
            python3 reset.py
            python3 setup_volumes.py # only use setup_volumes.py if you need to provision volumes and attach them to a folder.
    
    Part 2: Configure config.yaml
        
        Should any modifications be made in this section, it will be essential to re-execute Part 3.

        Execute the following command:
            nano config.yaml
        
        You will have to fill out the following parameters inside this configuration file where there are double quotes ""

        Source Configuration:
            Source Bucket Name: Specify the name of the originating bucket where your data is stored.
            Source Bucket Prefix: Indicate the subdirectory within your source bucket. Omit the preceding '/', but ensure to include a trailing '/'.
            Source Region: Denote the geographic location of your bucket, for example, "us-east-1". For buckets located in a snowball, use "snow" as the region.
            Source Access Key: Provide the access key associated with a user who has S3 permissions for the source S3 bucket.
            Source Secret Access Key: Supply the secret access key corresponding to the user with S3 permissions for the source S3 bucket.
            
        Local Configuration:
            Intermediary Directory: This directory acts as a temporary storage area during data transfer. Its configuration is crucial if utilizing a single volume compute.
        
        Destination Configuration:
            Destination Bucket Name: Enter the name of the bucket where you intend your data to be transferred.
            Destination Bucket Prefix: Specify the subdirectory within your destination bucket. Do not include a preceding '/', but ensure a trailing '/' is added.
            Destination Region: Indicate the geographic location of your destination bucket, such as "us-east-1". Note that snowball is not supported as a destination.
            Destination Access Key: Provide the access key for a user with S3 permissions to the destination S3 bucket.
            Destination Secret Access Key: Supply the secret access key for the user with S3 permissions to the destination S3 bucket.
        
        Transfer Settings:
            Max Transfer Size (Source to Local): Define the maximum file size (in bytes) allowed for a single transfer from the source to the local storage.
            Max Transfer Size (Local to Destination): [Not Implemented] State the maximum total file size (in gigabytes) permitted for a single transfer from the local storage to the destination.
            Destination Endpoint URL: Enter the endpoint URL for the destination S3 bucket. If not applicable, set as 'no_endpoint'.
            Source Endpoint URL: Provide the endpoint URL for the source S3 bucket. If not applicable, set as 'no_endpoint'. For legacy snowball, use 'http' and the port number, whereas for others, use 'https' without specifying the port number.

    Part 3: Begin transfer
        
        To terminate the scripts, use Ctrl+C.
        Restarting the scripts doesn't require repeating Part 1 or Part 2, unless previously specified in the earlier sections.

        For transfers conducted on a machine equipped with a single volume:
            Utilize the src_sync_svol.py script to continuously transfer data from your source S3 bucket to your local directory.
            Concurrently, the dest_sync_svol.py script will be responsible for persistently transferring data from the local directory to the destination S3 bucket.
            To execute these concurrently, we will utilize sync_svol.py.
            Inherent logic, integrated with a ledger system, guarantees that data once transferred will not be redundantly moved.
            Additionally, the management of storage space from the source to the local directory is seamlessly handled and completed automatically.

            Execute the following command (if you are using anaconda use python instead of python3):
                python3 sync_svol.py

        In both scripts, you'll notice messages indicating the source and destination of data transfers. 
        When there's no data to transfer, the scripts will simply report that they're scanning for new data to move.

        For transfers conducted on a machine equipped with a multiple volume setup:
            Whenever possible, we utilize multiple volumes because each volume has restricted read/write capabilities. 
            By writing to several volumes simultaneously, we can achieve higher data transfer rates.

            Utilize the src_sync_mvol.py script to continuously transfer data from your source S3 bucket to your multiple volume directories.
            Concurrently, the dest_sync_mvol.py script will be responsible for persistently transferring data from all of the multiple volume directories to the destination S3 bucket.
            To execute these concurrently, we will utilize sync_mvol.py.
            Inherent logic, integrated with a ledger system, guarantees that data once transferred will not be redundantly moved.
            Additionally, the management of storage space from the source to the multiple volume directories is seamlessly handled and completed automatically.

            Execute the following command (if you are using anaconda use python instead of python3):
                python3 sync_mvol.py

        In both scripts, you'll notice messages indicating the source and destination of data transfers. 
        When there's no data to transfer, the scripts will simply report that they're scanning for new data to move.

=====================================================================================================================================================================================

Development Structure:

    Supporting python scripts:

        reset.py
            The script provides functionality to delete contents within specified directories and perform cleanup based on a configuration file. 
            It utilizes os for directory and file operations, shutil for removing directory trees, and a custom read_config function from a helper module.

        setup_volumes.py
            Python script automates partitioning, formatting, and mounting of block devices on Linux, also setting directory permissions. 
            It executes shell commands using subprocess, parses command output with json, and performs filesystem operations via os.

        helper.py
            Python module for interacting with local filesystem and AWS S3 buckets. It includes functions to read a YAML configuration file, 
            list objects in an S3 bucket (with support for S3 on Outposts), list local files excluding those ending with numbers, get disk usage details for a directory, 
            and aggregate local files across multiple volumes. The script employs libraries like yaml for configuration parsing, os for filesystem operations, 
            boto3 for AWS S3 interactions, subprocess for executing shell commands, and re for regular expressions.

        src_connect_test.py
            Python script to test connectivity to source s3 bucket.
            After putting the in the proper credentials necessary for an s3 bucket for cloud or snowball in config.yaml run the script to see if it correctly lists all the objects inside the bucket.

    Core python scripts:

        All scripts inherit functionality from helper.py to parse configurations, manage AWS S3 interactions, and managing filesystem operations.

        [src_sync_svol.py, src_sync_mvol.py]

            This Python script is designed to synchronize data from an Amazon S3 bucket to local storage volumes. 
            It reads configuration settings, establishes a connection to the S3 bucket using the Boto3 library, and calculates available space on local volumes. 
            The script then identifies files that are either missing or have a size discrepancy in the local storage compared to the S3 bucket, 
            generates a list of transfer commands, and executes them using the s5cmd tool. 
            Additionally, it maintains a ledger file to track the synchronization progress and performs a pseudo checksum to verify successful transfers, 
            removing any discrepancies from the ledger. The process repeats in a loop, checking for new data in the source bucket.

        [dest_sync_svol.py, dest_sync_mvol.py]

            This Python script facilitates the transfer of files from local storage volumes to an Amazon S3 bucket. 
            Initially, it reads configuration details and establishes a connection to the S3 bucket using the Boto3 library. 
            The script then identifies files in local storage that are either missing or have size differences in the S3 bucket, generates commands to transfer these files, 
            and executes them using the s5cmd tool. After the transfer, it attempts to delete the successfully transferred files from the local storage to prevent duplication. 
            The process repeats in a loop, consistently checking for new files to transfer.

        [sync_svol.py, sync_mvol.py]

            The provided Python code uses the subprocess module to simultaneously execute two scripts, 'src_sync_xvol.py' and 'dest_sync_xvol.py',
            and executes them perpetually until canceled.

        If multi volumes [src_sync_mvol.py, dest_sync_mvol.py] have already been provisioned to a different folder naming convention (formatted and attached to a folder) make the following edits to the code in the script that you are using:
            Find the following lines in the script and comment them out with a preceeding #:
                base_path = "/tmp/volume-"
                volumes = [base_path + str(i).zfill(2) for i in range(1, 100) if os.path.exists(base_path + str(i).zfill(2))]
            Add the following line with your folders you want to transfer data to or from locally.
                volumes = ['/mnt/path/to/your/volume', '/usr/another/path/to/folder', '/local/example']

    File transfer program:

        s5cmd
            s5cmd is a very fast S3 and local filesystem execution tool. It comes with support for a multitude of operations including tab completion and wildcard support for files, 
            which can be very handy for your object storage workflow while working with large number of files.

            All of the core python scripts invoke s5cmd to make file transfers.

=====================================================================================================================================================================================

To re-provision a Snowball when an S3 bucket is not found, you can follow these revised steps:
    AWS Configuration:

        Enter your access key, secret access key, and the region from which you ordered the Snowball.

    Get Software Updates:

        Execute: aws snowball get-software-updates --job-id <your job id>.
        You'll get a download link. Use this in the next step.
    
    Download the Update:

        Run: curl -o update-<job id> "<download link>".
        Replace <job id> with your specific job ID and <download link> with the link you received.
    
    Unlock the Device:

        Use: snowballedge unlock-device --manifest-file <manifest file path> --unlock-code <unlock code> --endpoint https://<snowball IP>.
        Keep checking the device state until it says "UNLOCKED".
    
    Download Updates to Snowball:

        Execute: snowballEdge download-updates --uri <update file path> --manifest-file <manifest file path> --unlock-code <unlock code> --endpoint https://<snowball IP>.
        Monitor the download state until it reads "DOWNLOADED".
    
    Install Updates:

        Run: snowballEdge install-updates --manifest-file <manifest file path> --unlock-code <unlock code> --endpoint https://<snowball IP>.
        Check the install state until it indicates "NA" and not "REQUIRE_REBOOT".
    
    Reboot the Device:

        Execute: snowballedge reboot-device --manifest-file <manifest file path> --unlock-code <unlock code> --endpoint https://<snowball IP>.
        After rebooting, configure your Snowball. You should now see an S3 bucket inside it.

    Example Using Windows OS:

        With specific job ID, unlock code, and endpoint IP details, follow the same steps, replacing placeholders with your actual values. The commands will look similar to the provided example, adjusted for your specific job ID, manifest file path, unlock code, and Snowball IP.
        This process ensures that your Snowball is correctly configured and updated, allowing you to access the S3 bucket as intended.

        job-id: JID0f3ad66a-25e4-47b9-bb25-4c00ac9bd921
        unlock-code: afab4-ad5e1-acfb0-7a68d-819b3
        endpoint: 10.20.1.20
        uri (where you will save the update to): C:/Users/JimZieleman/update-JID0f3ad66a-25e4-47b9-bb25-4c00ac9bd921
        manifest-file: C:\Users\JimZieleman\Downloads\JID0f3ad66a-25e4-47b9-bb25-4c00ac9bd921_manifest.bin

        aws snowball get-software-updates --job-id JID0f3ad66a-25e4-47b9-bb25-4c00ac9bd921
        curl -o update-JID0f3ad66a-25e4-47b9-bb25-4c00ac9bd921 "https://awsie-update-bundles-us-east-1-prod.s3.us-east-1.amazonaws.com/JID0f3ad66a-25e4-47b9-bb25-4c00ac9bd921/124/offline-updates?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Date=20231121T165631Z&X-Amz-SignedHeaders=host&X-Amz-Expires=172800&X-Amz-Credential=AKIA3SPWFXC5ZLZ33AFU%2F20231121%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Signature=8ee2a7930c62853ae652fcde92408559b1cf9b5becc828b3a62e50c7b299cccb"
        snowballedge unlock-device --manifest-file C:\Users\JimZieleman\Downloads\JID0f3ad66a-25e4-47b9-bb25-4c00ac9bd921_manifest.bin --unlock-code afab4-ad5e1-acfb0-7a68d-819b3 --endpoint https://10.20.1.20
        snowballEdge download-updates --uri file:///C:/Users/JimZieleman/update-JID0f3ad66a-25e4-47b9-bb25-4c00ac9bd921 --manifest-file C:\Users\JimZieleman\Downloads\JID0f3ad66a-25e4-47b9-bb25-4c00ac9bd921_manifest.bin --unlock-code afab4-ad5e1-acfb0-7a68d-819b3 --endpoint https://10.20.1.20
        snowballEdge install-updates --manifest-file C:\Users\JimZieleman\Downloads\JID0f3ad66a-25e4-47b9-bb25-4c00ac9bd921_manifest.bin --unlock-code afab4-ad5e1-acfb0-7a68d-819b3 --endpoint https://10.20.1.20
        snowballedge reboot-device --manifest-file C:\Users\JimZieleman\Downloads\JID0f3ad66a-25e4-47b9-bb25-4c00ac9bd921_manifest.bin --unlock-code afab4-ad5e1-acfb0-7a68d-819b3 --endpoint https://10.20.1.20
        snowballedge describe-device --manifest-file C:\Users\JimZieleman\Downloads\JID0f3ad66a-25e4-47b9-bb25-4c00ac9bd921_manifest.bin --unlock-code afab4-ad5e1-acfb0-7a68d-819b3 --endpoint https://10.20.1.20
        snowballedge describe-device-software --manifest-file C:\Users\JimZieleman\Downloads\JID0f3ad66a-25e4-47b9-bb25-4c00ac9bd921_manifest.bin --unlock-code afab4-ad5e1-acfb0-7a68d-819b3 --endpoint https://10.20.1.20






