import config
import pathlib
import sys
import hashlib
import argparse
import platform
import audio_providers
import helpers

# AudioProviders
languages = ["pt-BR", "en-US"]

# Audio provider just for testing (Windows only)
powershell_test_audio_provider = audio_providers.AudioProvider({
        "pt-BR": "powershell -c 'echo pt-BR [input_file_path] [input_file_parent]/[input_file_stem].mp3'",
        "en-US": "powershell -c 'echo en-US [input_file_path] [input_file_parent]/[input_file_stem].mp3'"
    },
    3,
    False
)

# Audio provider just for testing (Linux only)
bash_test_audio_provider = audio_providers.AudioProvider({
        "pt-BR": "bash -c 'echo pt-BR [input_file_path] [input_file_parent]/[input_file_stem].mp3'",
        "en-US": "bash -c 'echo en-US [input_file_path] [input_file_parent]/[input_file_stem].mp3'"
    },
    3,
    False
)

# https://github.com/rany2/edge-tts
# Command explanation:
#    mkdir: create the corresponding filesystem structure of the texts in the tmp folder
#    edge-tts: create the audio files in the tmp folder at the equivalent folder
#    mv: after a successful creation, move the file from the tmp (RAM backed) to the persistent storage alongside the input file
rany2_edge_tts_audio_provider = audio_providers.AudioProvider({
        "pt-BR": "bash -c \"mkdir -p /tmp/[input_file_parent] && edge-tts --voice pt-BR-FranciscaNeural --file [input_file_path] --write-media /tmp/[input_file_parent]/[input_file_stem].mp3 && mv /tmp/[input_file_parent]/[input_file_stem].mp3 [input_file_parent]/\"",
        "en-US": "bash -c \"mkdir -p /tmp/[input_file_parent] && edge-tts --voice en-US-AndrewNeural --file [input_file_path] --write-media /tmp/[input_file_parent]/[input_file_stem].mp3 && mv /tmp/[input_file_parent]/[input_file_stem].mp3 [input_file_parent]/\""
    },
    3,
    True
)

audio_providers_per_lang = {"pt-BR": rany2_edge_tts_audio_provider, "en-US": rany2_edge_tts_audio_provider}

# Get the file program arguments
parser = argparse.ArgumentParser(description="Manages automatically audio generation services/providers")
parser.add_argument('--text-path', required=True, type=pathlib.Path, help="Path to the folder containing .txt files for processing")
parser.add_argument('--hash-path', required=True, type=pathlib.Path, help="Path to the hash file (it is where we store the hashes of previous processed files, so we can process only the changed ones)")
parser.add_argument('--ignore-hashes', required=False, default=False, action='store_true', help="Skip the hash check (aka consider every file as changed)")
parser.add_argument('--ignore-audio-files', required=False, default=False, action='store_true', help="Do not skip files that already have a audio file")
parser.add_argument('--retry', required=False, type=int, default=2, help="How many times we shloud retry a command before consider it failed")
parser.add_argument('--polling-rate', required=False, type=int, default=5, help="Polling interval in seconds") # Seconds
parser.add_argument('--test', required=False, action='store_true', default=False, help="Changes the audio providers to testing ones (it auto-selects based on the platform)")

args = parser.parse_args()

# If we use the test flag, use one of these providers for each platform
if args.test == True:
    match platform.system():

        case "Windows":
            audio_providers_per_lang = {"pt-BR": powershell_test_audio_provider, "en-US": powershell_test_audio_provider}

        case "Linux":
            audio_providers_per_lang = {"pt-BR": bash_test_audio_provider, "en-US": bash_test_audio_provider}

        case _:
            audio_providers_per_lang = {"pt-BR": bash_test_audio_provider, "en-US": bash_test_audio_provider}

# Is the argument really a folder?
if not args.text_path.is_dir():
    print("The text path must be a directory", file=sys.stderr)
    raise Exception

# Open the hash store
with open(args.hash_path, "r+", encoding="UTF-8") as file_hash_store_handle:
    hash_store = helpers.read_hash_store(args.hash_path)

    # Get the workload
    workload = helpers.get_files_to_gen_audio(args.text_path, hash_store, languages, args.ignore_audio_files, args.ignore_hashes)

    # Update the hash store if necessary
    helpers.update_hash_store(hash_store, workload.unchanged_hashes, file_hash_store_handle)

    helpers.process_text_files(workload.files_need_processing, args.polling_rate, audio_providers_per_lang, file_hash_store_handle, args.retry)