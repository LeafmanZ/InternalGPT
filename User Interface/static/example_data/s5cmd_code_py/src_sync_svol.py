import boto3
import os
import subprocess
import pandas as pd
import time
from helper import read_config, list_objects, get_local_files, get_disk_usage

def main():
    config = read_config()

    if not config:
        print("Failed to read the configuration.")
        return

    # set up source information
    bucket_src_name = config["source"]["bucket_name"]
    bucket_src_prefix = config["source"]["bucket_prefix"]
    bucket_src_region = config["source"]["region"]
    access_key_src = config["source"]["access_key"]
    secret_access_key_src = config["source"]["secret_access_key"]

    # set up source s3 url
    src_endpoint_url = config["transfer_settings"]["src_endpoint_url"]

    if src_endpoint_url == 'no_endpoint':
        s3_client_src = boto3.client('s3', 
        aws_access_key_id=access_key_src, 
        aws_secret_access_key=secret_access_key_src, 
        region_name=bucket_src_region)
    elif src_endpoint_url != 'no_endpoint' and bucket_src_region != 'snow': 
        # create aws clients to see source objects
        s3_client_src = boto3.client('s3', 
        aws_access_key_id=access_key_src, 
        aws_secret_access_key=secret_access_key_src, 
        region_name=bucket_src_region, 
        endpoint_url=src_endpoint_url, 
        use_ssl=False, verify=False)
    else:
        # Initialize a session using your credentials (for the sake of this example, I'm using hardcoded credentials; in production, use IAM roles or other secure ways)
        session = boto3.Session(
            aws_access_key_id=access_key_src, 
            aws_secret_access_key=secret_access_key_src
        )

        # Connect to S3 with the specified endpoint
        if 'https' in src_endpoint_url: # denotes new snowballs
            s3_client_src = session.resource('s3', endpoint_url=src_endpoint_url, verify=False)
        else:
            s3_client_src = session.resource('s3', endpoint_url=src_endpoint_url)

    # set up local information
    local_directory = config["local"]["directory"]

    # set up maximum data transfer amount per run from source edge s3 to localstore
    max_size_to_transfer_src2l = config["transfer_settings"]["max_size_to_transfer_src2l"]

    while True:
        usage = get_disk_usage(local_directory)
        if usage:
            # Convert KB to GB
            available_gb = usage['available'] / (1024 * 1024)

            # Multiply by 0.9 and convert to int to get the number of GB that can fit.
            # Select the smallest size to move between space available, or max_size_to_transfer_src2l
            chosen_size = min(int(available_gb * 0.9), max_size_to_transfer_src2l)
            chosen_size_bytes = chosen_size * (2**30)

            print(f"Directory {local_directory} resides on filesystem {usage['filesystem']} which has:")
            print(f"Total Space: {usage['total'] / (1024 * 1024):.2f} GB")
            print(f"Used Space: {usage['used'] / (1024 * 1024):.2f} GB")
            print(f"Available Space: {available_gb:.2f} GB")
            print(f"Approximately {chosen_size} files of 1GB each can be stored in the directory.")
        else:
            print(f"Failed to get disk usage for {local_directory}")

        # get the objects in our source bucket and local directory to compare missing objects and sync them from source to local
        objects_in_src = list_objects(bucket_src_name, bucket_src_prefix, s3_client_src, isSnow=(bucket_src_region=='snow'))
        local_files = get_local_files(local_directory)

        # Get keys in S3 bucket not in local or with different sizes, also checks if they keys have already been moved as recorded in the source ledger
        if os.path.isfile('src_ledger.csv'):
            src_ledger_df = pd.read_csv('src_ledger.csv')
            src_difference = {key for key in objects_in_src if (key not in local_files or objects_in_src[key] != local_files[key]) and (key not in src_ledger_df['Key'].values)}
        else:
            src_difference = {key for key in objects_in_src if (key not in local_files or objects_in_src[key] != local_files[key])}

        # # Clear the content of src_commands.txt before writingna
        with open('src_commands.txt', 'w') as file:
            pass

        if src_difference and (chosen_size > 0):
            data = [(key, objects_in_src[key]) for key in src_difference]
            data.sort(key=lambda x: x[1], reverse=True) # Sort descending by size

            cumulative_size = 0
            filtered_data = []

            for item in data:
                key, size = item
                if cumulative_size + size <= chosen_size_bytes:
                    filtered_data.append(item)
                    cumulative_size += size
                else:
                    break

            with open('src_commands.txt', 'w') as file:
                for obj_key, obj_size in filtered_data:
                    src_path = f"s3://{bucket_src_name}/{bucket_src_prefix}{obj_key}"
                    dst_path = f"{local_directory}{obj_key}"

                    command = f"cp --concurrency 1 --source-region {bucket_src_region} '{src_path}' '{dst_path}'"
                    file.write(command + '\n')
            print(f"Commands have been written to src_commands.txt.")
            
            # Setting up AWS environment variables to use s5cmd to move from source to local
            os.environ["AWS_ACCESS_KEY_ID"] = access_key_src
            os.environ["AWS_SECRET_ACCESS_KEY"] = secret_access_key_src

            # Execute the shell src_command
            if src_endpoint_url == 'no_endpoint':
                src_command = "time ./s5cmd --stat --numworkers 1024 run src_commands.txt"
            elif src_endpoint_url != 'no_endpoint' and bucket_src_region != 'snow':
                src_command = f"time ./s5cmd --stat --endpoint-url={src_endpoint_url} --no-verify-ssl --numworkers 1024 run src_commands.txt"
            else:
                if 'https' in src_endpoint_url: # denotes new snowballs
                    src_command = f"time ./s5cmd --stat --endpoint-url={src_endpoint_url} --no-verify-ssl --numworkers 1024 run src_commands.txt"
                else:
                    src_command = f"time ./s5cmd --stat --endpoint-url={src_endpoint_url} --numworkers 1024 run src_commands.txt"                
            os.system(src_command)

            # do pseudo checksum to ensure that the files were moved correctly, if not remove rows with Key and respective Size from src_ledger.csv
            local_files = get_local_files(local_directory)
            if os.path.isfile('src_ledger.csv'):
                src_difference_afterrun = {key for key in objects_in_src if (key not in local_files or objects_in_src[key] != local_files[key]) and (key not in src_ledger_df['Key'].values)}
            else:
                src_difference_afterrun = {key for key in objects_in_src if (key not in local_files or objects_in_src[key] != local_files[key])}
            current_run_src_ledger_df = pd.DataFrame(filtered_data, columns=['Key', 'Size'])

            # If CSV doesn't exist, write the header, otherwise skip
            if not os.path.isfile('src_ledger.csv'):
                current_run_src_ledger_df.to_csv('src_ledger.csv', index=False)
            else:
                current_run_src_ledger_df.to_csv('src_ledger.csv', mode='a', header=False, index=False)
            print('Objects set to move have been recorded to src_ledger.csv')

            # Read the CSV into a DataFrame
            src_ledger_df = pd.read_csv('src_ledger.csv')

            # Sort by 'Size' and drop duplicates by 'Key', keeping the row with the largest 'Size'
            src_ledger_df = src_ledger_df.sort_values(by='Size', ascending=False)
            src_ledger_df = src_ledger_df.drop_duplicates(subset='Key', keep='first')

            if src_difference_afterrun:
                # Filter out rows that have a Key in src_difference_afterrun
                src_ledger_df = src_ledger_df[~src_ledger_df['Key'].isin(src_difference_afterrun)]
                print(f"Rows with keys {src_difference_afterrun} removed from src_ledger.csv")
            else:
                print(f"All objects have been moved successfully.")
            
            # Save the updated DataFrame back to the CSV
            src_ledger_df.to_csv('src_ledger.csv', index=False)
        else:
            print(f"All objects in {bucket_src_name}/{bucket_src_prefix} are identical in {local_directory}. Or all objects that can possibly be moved to {local_directory} have been moved.")

        print('Waiting 1 second before checking for new additions of data in the source bucket.')
        time.sleep(1)

if __name__ == "__main__":
    main()