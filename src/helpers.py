
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

def files_to_process_total_len(files_for_processing):

    # Perform type checking to avoid runtime errors
    if type(files_for_processing) is not dict:
        raise TypeError

    total_size = 0

    for file_list in self.files_per_lang:
        if type(file_list) is not list:
            raise TypeError

        total_size = len(file_list)

    return total_len

def get_files_to_gen_audio(text_path, file_hash_store, languages, ignore_audio_files=False, ignore_hash=False):

    files_for_processing = {}

    # Populate the variable with language specific lists
    for lang in languages:
        files_for_processing[lang] = []

    for (root,dirs,files) in os.walk(text_path, topdown=True):

        # Look only for txt files
        if pathlib.Path(file).suffix == ".txt":

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

                # So this is a new file without any audio

                # Get the lang
                lang = get_file_lang(file_stem)

                # Put the files in the correct language "bucket" for later processing
                files_for_processing[lang].append(file_path)

    return FilesForProcessing(files_for_processing)

# The file_hash_store_handle must be opened in append only mode!
def process_text_files(files_for_processing, polling_interval, audio_providers_per_lang, file_hash_store_handle, retry_limit):

    # Loop until all files are processed
    while(files_to_process_total_len(files_for_processing) > 0):

        # Load files until we don't have more capacity
        for lang, audio_provider in audio_providers_per_lang.items():

            # Load files until we run out of files or until we reach the maximum capacity
            while( audio_provider.has_capacity() and len(files_for_processing[lang]) > 0):
                input_file = files_for_processing[lang].pop()
                output_file = pathlib.Path(input_file).with_suffix(".mp3") #TODO: make the file extension configurable
                audio.run_task( input_file, output_file, lang, retry_limit )

        # What has finished?
        # I haven't reused the previous loop bacause this allows all the files for all languages to be loaded first
        for audio_provider in audio_providers_per_lang():

            results = audio_provider.get_tasks_results()

            # If all the tasks are still executing, an empty list will be returned. In which case, the for loop will be skipped
            for task_res in results:

                # Display information for the user
                if task_res.status == audio_providers.TaskResult.FAIL:
                    print(f"(FAIL) - command: {task_res.task.command} - return code: {task_res.return_code}")

                if task_res.status == audio_providers.TaskResult.RETRY:
                    print(f"(RETRY) - command: {task_res.task.command} - Attempts: {task_res.task.retry_attempts}/{task_res.task.retry_limit}")

                if task_res.status == audio_providers.TaskResult.SUCCESS:
                    print(f"(SUCCESS) - command: {task_res.task.command}")
                    # Append the file hash to the store, so other executions will skip it if it remains unchanged
                    # We can only do that AFTER the audio was generated (it also means that it can only occour in successful runs)
                    file_hash_store_handle.write( f"{task_res.task.data["input_file"]}\t{get_file_hash(task_res.task.data["input_file"])}" )

        # Wait sometime before querying the tasks again
        # The "if" is usefull not only to prevent exceptions, but also in making tests faster
        if polling_interval != 0:
            Time.sleep(polling_interval)