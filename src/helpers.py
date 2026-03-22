
class TsvParser_InvalidHashFile(Exception):
    pass

# A TSV (tab separated values) file will hold the information about file hashes in a format like this
# FILE/PATH	HASH
# Why TSV? Because the execution info can be appended to a file avoinding a complete overwrite every time we add a new information

# Takes the hashes from a TSV file and converts it into a dict object
# This is not a generic TSV parser!
def tsv_to_dict(tsv_content_str):

    # The file path is the key
    # The hash is the value
    path_hash_pair = {}

    rows = tsv_content_str.split("\n")

    for row in rows:
        columns_value = row.split("\t")

        # There should only be two values
        if len(columns_value) != 0:
            raise TsvParser_InvalidHashFile

        path_hash_pair[ columns_value[0] ] = columns_value[1]

    return path_hash_pair

def read_hash_store(hash_store_path):
    with open(hash_store_path, "r", encoding="UTF-8") as hf:
        return tsv_to_dict( hf.read() )

# Opening the same file multiple times isn't good for performance, but doing it any other way makes the code confusing
def get_file_hash(path):
    with open(path, "r", encoding="UTF-8") as file_handle:
        hashlib.file_digest(file_handle, "sha256").hexdigest()

# The files have the language written at the end og the file like this: '*_pt-BR', '*_en-US'
# However, some don't. In this case, consider them pt-BR
def get_file_lang(file_stem):
    presumed_lang = file_stem[-5:]

    match presumed_lang:

        case "pt-BR":
            return "pt-BR"

        case "en-US":
            return "en-US"

        case _:
            return "pt-BR"

def get_files_to_gen_audio(text_path, file_hash_store, languages, ignore_audio_files=False, ignore_hash=False):

    files_for_processing = {}

    # Populate the variable with language specific lists
    for lang in languages:
        files_for_processing[lang] = []

    for (root,dirs,files) in os.walk(text_path, topdown=True):

        # Look only for txt files
        if pathlib.Path(file).suffix == ".txt"

            file_path = f"{root}/{file_stem}.txt"
            with open(file_path, "r", encoding="UTF-8") as file_handle:

                file_stem = pathlib.Path(file).stem # The name without the path or the suffix (folder/text.txt -> text)

                # Do they have a corresponding audio file (mp3, wav)?
                if (pathlib.Path(f"{root}/{file_stem}.mp3").exists() or pathlib.Path(f"{root}/{file_stem}.mp3").exists()) and not ignore_audio_files:

                    # Do not overwrite the audio files, so continue
                    continue

                # Have they changed since the last execution (aka is their hash different or is it absent from the store)?
                file_hash = get_file_hash(file_path)

                if file_hash in file_hash_store and file_hash == file_hash_store[file_path] and not ignore_hash:

                    # The file exists in the store and hasn't changed
                    # It means that it was already processed (even though it does not have a audio file)
                    continue

                # So this is a new file without any audio, generate the audio then!

                # Get the lang
                lang = get_file_lang(file_stem)

                # Put the files in the correct language "bucket" for later processing
                files_for_processing[lang].append(file_path)

    return files_for_processing