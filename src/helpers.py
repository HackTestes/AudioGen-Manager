import os
import pathlib
import hashlib
import audio_providers

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

    # Avoid getting empty rows
    tsv_content_str = tsv_content_str.strip()

    rows = tsv_content_str.split("\n")

    for row in rows:

        # Just skip possible empty rows
        if len(row) == 0:
            continue

        columns_value = row.split("\t")

        # There should only be two values
        if len(columns_value) != 2:
            raise TsvParser_InvalidHashFile

        path_hash_pair[ columns_value[0] ] = columns_value[1]

    return path_hash_pair

# Assume a "flat" dict (a simple key value - file:hash)
def dict_to_tsv(dictionary):
    tsv_str = ""

    for key, value in dictionary.items():
        tsv_str += f"{key}\t{value}\n"

    return tsv_str.strip()

def read_hash_store(hash_store_path):
    with open(hash_store_path, "r", encoding="UTF-8") as hf:
        return tsv_to_dict( hf.read() )

# Opening the same file multiple times isn't good for performance, but doing it any other way makes the code confusing
def get_file_hash(path):
    with open(path, "rb") as file_handle:
        return hashlib.file_digest(file_handle, "sha256").hexdigest()

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

def files_to_process_total_len(files_per_lang):

    # Perform type checking to avoid runtime errors
    if type(files_per_lang) is not dict:
        raise TypeError

    total_size = 0

    for file_list in files_per_lang.values():

        if type(file_list) is not list:
            raise TypeError

        total_size += len(file_list)

    return total_size

class Workload():
    def __init__(self, files_that_need_processing, files_unchanged):
        self.files_need_processing = files_that_need_processing
        self.files_unchanged = files_unchanged


def get_files_to_gen_audio(text_path, file_hash_store, languages, ignore_audio_files=False, ignore_hash=False):

    files_for_processing = {}
    unchanged_files = {}

    # Populate the variable with language specific lists
    for lang in languages:
        files_for_processing[lang] = []

    for (root,dirs,files) in os.walk(text_path, topdown=True):
        for file in files:

            # Look only for txt files
            if pathlib.Path(file).suffix == ".txt":

                file_stem = pathlib.Path(file).stem # The name without the path or the suffix (folder/text.txt -> text)
                file_path = f"{root}/{file_stem}.txt"

                with open(file_path, "r", encoding="UTF-8") as file_handle:

                    # Do they have a corresponding audio file (mp3, wav)?
                    if (pathlib.Path(f"{root}/{file_stem}.mp3").exists() or pathlib.Path(f"{root}/{file_stem}.mp3").exists()) and not ignore_audio_files:

                        # Do not overwrite the audio files, so continue
                        continue

                    # Have they changed since the last execution (aka is their hash different or is it absent from the store)?
                    file_hash = get_file_hash(file_path)

                    if file_path in file_hash_store and file_hash == file_hash_store[file_path] and not ignore_hash:

                        # The file exists in the store and hasn't changed
                        # It means that it was already processed (even though it does not have a audio file)
                        unchanged_files[ file_path ] = file_hash
                        continue

                    # So this is a new file without any audio

                    # Get the lang
                    lang = get_file_lang(file_stem)

                    # Put the files in the correct language "bucket" for later processing
                    files_for_processing[lang].append(file_path)

    return Workload(files_for_processing, unchanged_files)

def update_hash_store(file_hash_store, unchanged_files, file_hash_store_write_handle):

    # If they have the same elements; these elements are the same and they have the same amount, then they are the same (think of sets in math)
    # We only check this last condition in here
    if len(file_hash_store) == len(unchanged_files):
        # In this case we don't need to update anything on the file
        return

    # Some things have changed, we need to remove the changed entries
    # We can also just insert the unchanged files
    file_hash_store_write_handle.truncate(0) # Clear the file
    file_hash_store_write_handle.write( dict_to_tsv(unchanged_files) )

# The file_hash_store_handle must be opened in append only mode!
def process_text_files(files_for_processing, polling_interval, audio_providers_per_lang, file_hash_store_handle, retry_limit):

    # Loop until all files are processed
    while(files_to_process_total_len(files_for_processing) > 0):

        # Load files until we don't have more capacity
        for lang, audio_prov in audio_providers_per_lang.items():

            # Load files until we run out of files or until we reach the maximum capacity
            while( audio_prov.has_capacity() and len(files_for_processing[lang]) > 0):
                input_file = files_for_processing[lang].pop()
                output_file = input_file.replace(".txt", ".mp3") #TODO: make the file extension configurable
                audio_prov.run_task( input_file, output_file, lang, retry_limit )

        # What has finished?
        # I haven't reused the previous loop bacause this allows all the files for all languages to be loaded first
        for audio_prov in audio_providers_per_lang.values():

            results = audio_prov.get_tasks_results()

            # If all the tasks are still executing, an empty list will be returned. In which case, the for loop will be skipped
            for task_res in results:

                print(task_res.task.task_data)

                # Display information for the user
                if task_res.status == audio_providers.TaskSatus.FAIL:
                    print(f"(FAIL) - command: {task_res.task.command} - return code: {task_res.return_code}")

                if task_res.status == audio_providers.TaskSatus.RETRY:
                    print(f"(RETRY) - command: {task_res.task.command} - Attempts: {task_res.task.retry_attempts}/{task_res.task.retry_limit}")

                if task_res.status == audio_providers.TaskSatus.SUCCESS:
                    print(f"(SUCCESS) - command: {task_res.task.command}")
                    # Append the file hash to the store, so other executions will skip it if it remains unchanged
                    # We can only do that AFTER the audio was generated (it also means that it can only occour in successful runs)
                    file_hash_store_handle.seek(0, os.SEEK_END) # Put the file cursor always at the end
                    file_hash_store_handle.write( f"{task_res.task.task_data["input_file"]}\t{get_file_hash(task_res.task.task_data["input_file"])}\n" )

        # Wait sometime before querying the tasks again
        # The "if" is usefull not only to prevent exceptions, but also in making tests faster
        if polling_interval != 0:
            Time.sleep(polling_interval)