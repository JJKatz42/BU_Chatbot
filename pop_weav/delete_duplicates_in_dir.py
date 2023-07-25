import os
import hashlib
import glob

# Directory that contains files
directory = '/workspaces/BU_Chatbot/weavdb_direct'

def get_file_hash(fp):
    """Compute hash of file content using SHA256 algorithm."""
    hasher = hashlib.sha256()
    with open(fp, 'rb') as f:
        while True:
            data = f.read(65536)  # read in chunks
            if not data:
                break
            hasher.update(data)
    return hasher.hexdigest()

# Dict to store file hashes
file_hashes = {}

# Iterate over all files in the directory
for filepath in glob.glob(os.path.join(directory, '*')):
    file_hash = get_file_hash(filepath)

    if file_hash in file_hashes:
        # This file is a duplicate of an earlier file
        os.remove(filepath)
        print(f'Removed duplicate file: {filepath}')
    else:
        # This file is not a duplicate
        file_hashes[file_hash] = filepath
