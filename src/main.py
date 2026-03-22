import config
import pathlib
import sys
import hashlib
import argparse

# Start the default configuration
configuration = Configuration()

# Get the file program arguments
parser = argparse.ArgumentParser(description="Manages automatically audio generation services/providers")
parser.add_argument('--text-path', required=True, type=pathlib.Path, nargs=1)
parser.add_argument('--hash-path', required=True, type=pathlib.Path, nargs=1)
parser.add_argument('--ignore-hashes', required=False, type=pathlib.Path, action='store_true')
args = parser.parse_args()


# Is the argument really a folder?
if not args.text_path.is_dir():
    print("The text path must be a directory", file=sys.stderr)
    raise Exception
configuration.text_path = args.text_path

# Open the hash store
file_hash_store = helpers.read_hash_store(configuration.hash_path)

# Holds references to child processes tasks
# This will be used to manage multiple processes that generate audio
tasks = []