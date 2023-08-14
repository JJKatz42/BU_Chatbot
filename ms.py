import os
import shutil

def move_files(source_directory, destination_directory):
    try:
        # Check if both directories exist
        if not os.path.exists(source_directory):
            raise FileNotFoundError(f"Source directory '{source_directory}' does not exist.")
        if not os.path.exists(destination_directory):
            raise FileNotFoundError(f"Destination directory '{destination_directory}' does not exist.")

        # Get a list of all files in the source directory
        files = os.listdir(source_directory)

        # Move each file to the destination directory
        for file in files:
            source_path = os.path.join(source_directory, file)
            destination_path = os.path.join(destination_directory, file)
            shutil.move(source_path, destination_path)

        print("All files moved successfully.")
    except Exception as e:
        print(f"An error occurred: {e}")

def count_num_files_in_directory(directory):
    try:
        # Check if the directory exists
        if not os.path.exists(directory):
            raise FileNotFoundError(f"Directory '{directory}' does not exist.")

        # Get a list of all files in the directory
        files = os.listdir(directory)

        # Print the number of files in the directory
        print(f"There are {len(files)} files in the directory.")
    except Exception as e:
        print(f"An error occurred: {e}")

# Replace these paths with your source and destination directories
source_directory = "/Users/jonahkatz/Desktop/BU_Chatbot/beta_info"
destination_directory = "/Users/jonahkatz/Desktop/BU_Chatbot/new_webpages4"

# move_files(source_directory, destination_directory)

count_num_files_in_directory(source_directory)

count_num_files_in_directory(destination_directory)
#
# move_files(source_directory, destination_directory)
#
# count_num_files_in_directory(destination_directory)
