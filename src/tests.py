import unittest
import unittest.mock
import copy
import helpers
import audio_providers

# The hashes are all the same, because all of them are empty files
# sha256
precomputed_hash_store = {
            "./test_data/texts/file_hashed_001.txt": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "./test_data/texts/file_hashed_002.txt": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "./test_data/texts/file_hashed_003.txt": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        }

class TestMethods(unittest.TestCase):

    @unittest.mock.patch("subprocess.Popen")
    def test_process_text_files_regular_case(self, popen_mock):

        polling_interval = 0
        retry_limit = 3
        file_hash_store_handle_mock = unittest.mock.mock_open()() # Creates the open mock an then tries to "open" a file
        workload = helpers.get_files_to_gen_audio("./test_data/texts", precomputed_hash_store, ["pt-BR", "en-US"])
        pt_BR_audio_provider = audio_providers.AudioProvider({"pt-BR": "echo pt-BR [input_file_path] [output_file_path]"}, 1, False)
        en_US_audio_provider = audio_providers.AudioProvider({"en-US": "echo en-US   [input_file_path] [output_file_path]"}, 1, False)

        audio_providers_per_lang = {"pt-BR": pt_BR_audio_provider, "en-US": en_US_audio_provider}

        # Success
        # This means that every call will succeed
        popen_mock.return_value.poll.return_value = 0
        popen_mock.return_value.communicate.return_value = (None, None)

        helpers.process_text_files(workload.files_need_processing, polling_interval, audio_providers_per_lang, file_hash_store_handle_mock, retry_limit)

        popen_mock.assert_called()
        file_hash_store_handle_mock.write.assert_has_calls([
            unittest.mock.call("./test_data/texts/file_pt-BR.txt\te3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855\n"),
            unittest.mock.call("./test_data/texts/file_en-US.txt\te3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855\n"),
            unittest.mock.call("./test_data/texts/file.txt\te3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855\n")
        ])


    def test_read_hash_store(self):
        parsed_hash_store = helpers.read_hash_store("./test_data/file_hash_store.tsv")
        self.assertEqual(parsed_hash_store, precomputed_hash_store)

    def test_update_hash_store_needs_update(self):
        parsed_hash_store = helpers.read_hash_store("./test_data/file_hash_store.tsv")
        parsed_hash_store.popitem()

        file_handle_mock = unittest.mock.mock_open()() # Creates the open mock an then tries to "open" a file

        helpers.update_hash_store(precomputed_hash_store, parsed_hash_store, file_handle_mock)
        file_handle_mock.truncate.assert_called_with(0)
        file_handle_mock.write.assert_called()
        file_handle_mock.write.assert_called_with( helpers.dict_to_tsv(parsed_hash_store) )

    def test_update_hash_store_no_update(self):

        file_handle_mock = unittest.mock.mock_open()() # Creates the open mock an then tries to "open" a file

        helpers.update_hash_store(precomputed_hash_store, precomputed_hash_store, file_handle_mock)
        file_handle_mock.write.assert_not_called()

    def test_get_files_to_gen_audio_regular_case(self):

        workload = helpers.get_files_to_gen_audio("./test_data/texts", precomputed_hash_store, ["pt-BR", "en-US"])
        self.assertEqual(workload.files_need_processing, {
            "pt-BR": ["./test_data/texts/file.txt", "./test_data/texts/file_pt-BR.txt"],
            "en-US": ["./test_data/texts/file_en-US.txt"]
        })
        self.assertEqual(workload.files_unchanged, precomputed_hash_store)

    def test_get_files_to_gen_audio_ignore_hash_store(self):

        workload = helpers.get_files_to_gen_audio("./test_data/texts", precomputed_hash_store, ["pt-BR", "en-US"], ignore_hash=True)
        self.assertEqual(workload.files_need_processing, {
            "pt-BR": ["./test_data/texts/file.txt", "./test_data/texts/file_hashed_001.txt", "./test_data/texts/file_hashed_002.txt", "./test_data/texts/file_hashed_003.txt", "./test_data/texts/file_pt-BR.txt"],
            "en-US": ["./test_data/texts/file_en-US.txt"]
        })
        self.assertEqual(workload.files_unchanged, {})

    def test_get_files_to_gen_audio_ignore_audio_file(self):

        workload = helpers.get_files_to_gen_audio("./test_data/texts", precomputed_hash_store, ["pt-BR", "en-US"], ignore_audio_files=True)
        self.assertEqual(workload.files_need_processing, {
            "pt-BR": ["./test_data/texts/file.txt", "./test_data/texts/file_002.txt", "./test_data/texts/file_003.txt", "./test_data/texts/file_pt-BR.txt"],
            "en-US": ["./test_data/texts/file_en-US.txt"]
        })
        self.assertEqual(workload.files_unchanged, precomputed_hash_store)


    def test_tsv_to_dict(self):
        tsv_str = ("./project_root/texts/file\t0000000000\n"
                "./project_root/texts/file_002\t0000000000\n"
                "./project_root/texts/file_003\t0000000000\n"
                "\n\n\n"
        )

        expect = {
            "./project_root/texts/file": "0000000000",
            "./project_root/texts/file_002": "0000000000",
            "./project_root/texts/file_003": "0000000000"
        }

        self.assertEqual(helpers.tsv_to_dict(tsv_str), expect)

    def test_tsv_to_dict_skip_empty_rows(self):
        tsv_str = ("./project_root/texts/file\t0000000000\n"
                "./project_root/texts/file_002\t0000000000\n"
                "\n\n\n"
                "./project_root/texts/file_003\t0000000000\n"
                "\n\n\n"
        )

        expect = {
            "./project_root/texts/file": "0000000000",
            "./project_root/texts/file_002": "0000000000",
            "./project_root/texts/file_003": "0000000000"
        }

        self.assertEqual(helpers.tsv_to_dict(tsv_str), expect)

    def test_dict_to_tsv(self):
        expect = ("./project_root/texts/file\t0000000000\n"
                "./project_root/texts/file_002\t0000000000\n"
                "./project_root/texts/file_003\t0000000000"
        )

        dictionary = {
            "./project_root/texts/file": "0000000000",
            "./project_root/texts/file_002": "0000000000",
            "./project_root/texts/file_003": "0000000000"
        }

        self.assertEqual(helpers.dict_to_tsv(dictionary), expect)

    def test_get_file_lang(self):
        self.assertEqual(helpers.get_file_lang("file"), "pt-BR")
        self.assertEqual(helpers.get_file_lang("file_en-US"), "en-US")
        self.assertEqual(helpers.get_file_lang("file_pt-BR"), "pt-BR")

    def test_audio_provider_creation(self):

        capacity = 2
        audio_provider = audio_providers.AudioProvider({"pt-BR": "echo [input_file_path]"}, capacity, False)

        self.assertEqual(audio_provider.task_handles, [None]*2)
        self.assertEqual(audio_provider.task_empty_slot, set([0, 1]))

    @unittest.mock.patch("subprocess.Popen")
    def test_audio_provider_regular_case(self, popen_mock):

        capacity = 1
        audio_provider = audio_providers.AudioProvider({"pt-BR": "echo [input_file_path] [output_file_path]"}, capacity, False)

        audio_provider.run_task("input/file/path/text.txt", "pt-BR", 2)

        # Simulate an unfinshed process
        popen_mock.return_value.poll.return_value = None

        results = audio_provider.get_tasks_results()
        self.assertEqual(0, len(results))

        # Simulate a fail for retry
        popen_mock.return_value.poll.return_value = 1

        results = audio_provider.get_tasks_results()
        self.assertEqual(1, len(results))
        self.assertEqual(audio_providers.TaskSatus.RETRY, results[0].status)
        self.assertEqual(1, results[0].return_code)

        # Simulate a successful finish
        popen_mock.return_value.poll.return_value = 0

        results = audio_provider.get_tasks_results()
        self.assertEqual(1, len(results))
        self.assertEqual(audio_providers.TaskSatus.SUCCESS, results[0].status)
        self.assertEqual(0, results[0].return_code)

        # Is the audio provider in a good state?
        self.assertEqual(len(audio_provider.task_empty_slot), capacity)
        self.assertEqual(audio_provider.has_capacity(), True)

    @unittest.mock.patch("subprocess.Popen")
    def test_audio_provider_popen_error_on_retry(self, popen_mock):

        capacity = 3
        audio_provider = audio_providers.AudioProvider({"pt-BR": "echo [input_file_path] [output_file_path]"}, capacity, False)

        audio_provider.run_task("input/file/path/text.txt", "pt-BR", 5)

        # Simulate a fail for retry
        popen_mock.return_value.poll.return_value = 1

        # Raise an error during the retry
        popen_mock.side_effect = FileNotFoundError

        results = audio_provider.get_tasks_results()
        self.assertEqual(1, len(results))
        self.assertTrue(isinstance(results[0].exception, FileNotFoundError))

        # Is the audio provider in a good state?
        self.assertEqual(len(audio_provider.task_empty_slot), capacity)
        self.assertEqual(audio_provider.has_capacity(), True)

    @unittest.mock.patch("subprocess.Popen")
    def test_audio_provider_retry_until_failure(self, popen_mock):

        capacity = 3
        audio_provider = audio_providers.AudioProvider({"pt-BR": "echo [input_file_path] [output_file_path]"}, capacity, False)

        audio_provider.run_task("input/file/path/text.txt", "pt-BR", 1)
        audio_provider.run_task("input/file/path/text.txt", "pt-BR", 1)

        # Simulate a fail for retry
        popen_mock.return_value.poll.return_value = 1

        results = audio_provider.get_tasks_results()
        self.assertEqual(2, len(results))
        self.assertEqual(audio_providers.TaskSatus.RETRY, results[0].status)
        self.assertEqual(1, results[0].return_code)

        results = audio_provider.get_tasks_results()
        self.assertEqual(2, len(results))
        self.assertEqual(audio_providers.TaskSatus.FAIL, results[0].status)
        self.assertEqual(1, results[0].return_code)

        # Is the audio provider in a good state?
        self.assertEqual(len(audio_provider.task_empty_slot), capacity)
        self.assertEqual(audio_provider.has_capacity(), True)


    @unittest.mock.patch("subprocess.Popen")
    def test_audio_provider_command_replacement(self, popen_mock):

        capacity = 10
        audio_provider = audio_providers.AudioProvider({"pt-BR": "echo [input_file_path] [input_file_stem] [input_file_name] [input_file_parent]"}, capacity, False)

        command = audio_provider.run_task("input/file/path/text.txt", "pt-BR", 5)
        self.assertEqual(command, "echo input/file/path/text.txt text text.txt input/file/path")

        command = audio_provider.run_task("./input/file/path/text.txt", "pt-BR", 5)
        self.assertEqual(command, "echo input/file/path/text.txt text text.txt input/file/path")

    # Does a popen error cause the AudioProvider to be in a broken state?
    @unittest.mock.patch("subprocess.Popen")
    def test_audio_provider_popen_error_state(self, popen_mock):

        capacity = 1
        audio_provider = audio_providers.AudioProvider({"pt-BR": "echo [input_file_path]"}, capacity, False)

        self.assertEqual(len(audio_provider.task_empty_slot), 1)
        self.assertEqual(audio_provider.has_capacity(), True)

        popen_mock.side_effect = FileNotFoundError

        with self.assertRaises(FileNotFoundError) as e:
            audio_provider.run_task("input/file/path/text.txt", "pt-BR", 5)

        self.assertEqual(len(audio_provider.task_empty_slot), 1)
        self.assertEqual(audio_provider.has_capacity(), True)


    @unittest.mock.patch("subprocess.Popen")
    def test_audio_provider_capacity(self, popen_mock):

        capacity = 2
        audio_provider = audio_providers.AudioProvider({"pt-BR": "echo [input_file_path]"}, capacity, False)

        self.assertEqual(len(audio_provider.task_empty_slot), 2)
        self.assertEqual(audio_provider.has_capacity(), True)

        audio_provider.run_task("input/file/path/text.txt", "pt-BR", 5)

        self.assertEqual(len(audio_provider.task_empty_slot), 1)
        self.assertEqual(audio_provider.has_capacity(), True)

        audio_provider.run_task("input/file/path/text.txt", "pt-BR", 5)

        self.assertEqual(len(audio_provider.task_empty_slot), 0)
        self.assertEqual(audio_provider.has_capacity(), False)

    @unittest.mock.patch("subprocess.Popen")
    def test_audio_provider_error_no_capacity_left(self, popen_mock):

        capacity = 1
        audio_provider = audio_providers.AudioProvider({"pt-BR": "echo [input_file_path]"}, capacity, False)

        self.assertEqual(len(audio_provider.task_empty_slot), 1)
        self.assertEqual(audio_provider.has_capacity(), True)

        audio_provider.run_task("input/file/path/text.txt", "pt-BR", 5)

        self.assertEqual(len(audio_provider.task_empty_slot), 0)
        self.assertEqual(audio_provider.has_capacity(), False)

        with self.assertRaises(audio_providers.AudioProvider_NoCapacityLeft) as e:
            audio_provider.run_task("input/file/path/text.txt", "pt-BR", 5)

    @unittest.mock.patch("subprocess.Popen")
    def test_audio_provider_error_lang_not_supported(self, popen_mock):

        capacity = 1
        audio_provider = audio_providers.AudioProvider({"pt-BR": "echo [input_file_path]"}, capacity, False)

        with self.assertRaises(audio_providers.AudioProvider_LanguageNotSupported) as e:
            audio_provider.run_task("input/file/path/text.txt", "invalid-lang", 5)


if __name__ == "__main__":
    unittest.main()