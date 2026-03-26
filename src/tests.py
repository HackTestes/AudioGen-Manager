import unittest
import unittest.mock
import copy
import helpers
import audio_providers

class TestMethods(unittest.TestCase):

    def test_audio_provider_creation(self):

        capacity = 2
        audio_provider = audio_providers.AudioProvider({"pt-BR": "echo [input_file_path]"}, capacity, False)

        self.assertEqual(audio_provider.task_handles, [None]*2)
        self.assertEqual(audio_provider.task_empty_slot, set([0, 1]))

    @unittest.mock.patch('subprocess.Popen')
    def test_audio_provider_command_replacement(self, popen_mock):

        capacity = 1
        audio_provider = audio_providers.AudioProvider({"pt-BR": "echo [input_file_path] [output_file_path]"}, capacity, False)

        audio_provider.run_task("input/file/path", "output/file/path", "pt-BR", 5)

        self.assertEqual(audio_provider.task_handles[0].command, "echo \"input/file/path\" \"output/file/path\"")

    # Does a popen error cause the AudioProvider to be in a broken state?
    @unittest.mock.patch('subprocess.Popen')
    def test_audio_provider_popen_error_state(self, popen_mock):

        capacity = 1
        audio_provider = audio_providers.AudioProvider({"pt-BR": "echo [input_file_path]"}, capacity, False)

        self.assertEqual(len(audio_provider.task_empty_slot), 1)
        self.assertEqual(audio_provider.has_capacity(), True)

        popen_mock.side_effect = FileNotFoundError

        with self.assertRaises(FileNotFoundError) as e:
            audio_provider.run_task("input/file/path", "output/file/path", "pt-BR", 5)

        self.assertEqual(len(audio_provider.task_empty_slot), 1)
        self.assertEqual(audio_provider.has_capacity(), True)


    @unittest.mock.patch('subprocess.Popen')
    def test_audio_provider_capacity(self, popen_mock):

        capacity = 2
        audio_provider = audio_providers.AudioProvider({"pt-BR": "echo [input_file_path]"}, capacity, False)

        self.assertEqual(len(audio_provider.task_empty_slot), 2)
        self.assertEqual(audio_provider.has_capacity(), True)

        audio_provider.run_task("input/file/path", "output/file/path", "pt-BR", 5)

        self.assertEqual(len(audio_provider.task_empty_slot), 1)
        self.assertEqual(audio_provider.has_capacity(), True)

        audio_provider.run_task("input/file/path", "output/file/path", "pt-BR", 5)

        self.assertEqual(len(audio_provider.task_empty_slot), 0)
        self.assertEqual(audio_provider.has_capacity(), False)

    @unittest.mock.patch('subprocess.Popen')
    def test_audio_provider_error_no_capacity_left(self, popen_mock):

        capacity = 1
        audio_provider = audio_providers.AudioProvider({"pt-BR": "echo [input_file_path]"}, capacity, False)

        self.assertEqual(len(audio_provider.task_empty_slot), 1)
        self.assertEqual(audio_provider.has_capacity(), True)

        audio_provider.run_task("input/file/path", "output/file/path", "pt-BR", 5)

        self.assertEqual(len(audio_provider.task_empty_slot), 0)
        self.assertEqual(audio_provider.has_capacity(), False)

        with self.assertRaises(audio_providers.AudioProvider_NoCapacityLeft) as e:
            audio_provider.run_task("input/file/path", "output/file/path", "pt-BR", 5)

    @unittest.mock.patch('subprocess.Popen')
    def test_audio_provider_error_lang_not_supported(self, popen_mock):

        capacity = 1
        audio_provider = audio_providers.AudioProvider({"pt-BR": "echo [input_file_path]"}, capacity, False)

        with self.assertRaises(audio_providers.AudioProvider_LanguageNotSupported) as e:
            audio_provider.run_task("input/file/path", "output/file/path", "invalid-lang", 5)


if __name__ == '__main__':
    unittest.main()