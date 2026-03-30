import config
import pathlib
import sys
import hashlib
import argparse
import audio_providers
import helpers

# AudioProviders
languages = ["pt-BR", "en-US"]
powershell_test_audio_provider = audio_providers.AudioProvider({
        "pt-BR": "powershell -c 'echo pt-BR [input_file_path] [output_file_path]'",
        "en-US": "powershell -c 'echo en-US [input_file_path] [output_file_path]'"
    },
    3,
    True
)
audio_providers_per_lang = {"pt-BR": powershell_test_audio_provider, "en-US": powershell_test_audio_provider}

# Get the file program arguments
parser = argparse.ArgumentParser(description="Manages automatically audio generation services/providers")
parser.add_argument('--text-path', required=True, type=pathlib.Path)
parser.add_argument('--hash-path', required=True, type=pathlib.Path)
parser.add_argument('--ignore-hashes', required=False, default=False, action='store_true')
parser.add_argument('--ignore-audio-files', required=False, default=False, action='store_true')
parser.add_argument('--retry', required=False, type=int, default=12)
parser.add_argument('--polling-rate', required=False, type=int, default=5, help="Polling interval in seconds") # Seconds

args = parser.parse_args()

# Is the argument really a folder?
if not args.text_path.is_dir():
    print("The text path must be a directory", file=sys.stderr)
    raise Exception

# Open the hash store
with open(args.hash_path, "r+", encoding="UTF-8") as file_hash_store_handle:
    file_hash_store = helpers.read_hash_store(args.hash_path)

    # Get the workload
    workload = helpers.get_files_to_gen_audio(args.text_path, file_hash_store, languages, args.ignore_audio_files, args.ignore_hashes)

    # Update the hash store if necessary
    helpers.update_hash_store(file_hash_store, workload.files_unchanged, file_hash_store_handle)

    helpers.process_text_files(workload.files_need_processing, args.polling_rate, audio_providers_per_lang, file_hash_store_handle, args.retry)