class Configuration:

    def __init__(self):
        self.retry_attempts = 3
        self.retry_interval = 5 #In seconds
        self.audio_providers = {"en-US": None, "pt-BR": None} #Who is going to generate audio for each language?
        self.parallel_executions_limits {"remote": 4, "local": 1} # How many instances can we have running at the same time?
        self.text_path = None #Where are all the texts located
        self.hash_path = None #Where are the hashes stored (they are used to see if the files are different from the previous executions)