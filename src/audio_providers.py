from abc import ABC, abstractmethod
import shlex, subprocess
import sys

class AudioProvider_LanguageNotSupported(Exception):
    pass

class AudioProvider_NoCapacityLeft(Exception):
    pass

from enum import Enum

class TaskSatus(Enum):
    SUCCESS = 1
    FAIL = 2
    RETRY = 3

class TaskResult():
    def __init__(self, status, return_code, task):
        self.status = status
        self.return_code = return_code
        self.task = task

# This is responsible for managing a single subprocess
# It will hold critical information to help manage the task (like what was run, how many retries were made...)
class Task():

    # task_data will hold miscellaneous infomation that can be later returned to higher levels
    def __init__(self, command: str, retry_limit: int, task_data: dict):
        self.command = command
        self.retry_limit = retry_limit
        self.retry_attempts = 0
        self.task_data = task_data

        self.process_handle = subprocess.Popen(shlex.split(self.command), stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True, shell=False, encoding="UTF-8")

    def retry(self):

        # If we have attempts left and the process has finished
        if self.can_retry() and self.poll() != None:

            # Close the process
            self.process_handle.terminate()

            self.retry_attempts += 1

            # Retry
            self.process_handle = self.process_handle = subprocess.Popen(shlex.split(self.command), stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True, shell=False, encoding="UTF-8")

    def can_retry(self):

        if self.retry_attempts + 1 > self.retry_limit:
            return False

        return True

    def poll(self):
        return self.process_handle.poll()

    def data(self):
        return self.task_data

class AudioProvider():

    # Commands - which command will be used for each language: {"en-US": "<COMMAND>", "pt-BR": "<COMMAND>"}
    #    NOTE: the commands must follow a specific form, check the run_task function
    # execution_limit - how many parallel instances can we run for this provider. The limit is shared between all supported languages
    #    The execution limit is useful to avoid tripping DDoS protection in remote providers or exhausting the machine resources in local contexts
    # remote - does this provider work locally or remotely (uses an external server)
    def __init__(self, commands: dict, execution_limit: int, remote: bool):
        self.commands = commands
        self.execution_limit = execution_limit
        self.remote = remote
        self.task_handles = []
        self.task_empty_slot = set()

        # Populate the "buffers"/slots
        for i in range(0, execution_limit):
            self.task_handles.append(None) # Represents an empty task slot
            self.task_empty_slot.add(i) # Represents the indexes of empty slots

    # Adds a task to be executed by the provider
    def run_task(self, input_file_path, output_file_path, lang, retry_limit):

        if lang not in self.commands:
            raise AudioProvider_LanguageNotSupported()

        if not self.has_capacity():
            raise AudioProvider_NoCapacityLeft()

        current_command = self.commands[lang]

        # Replace the input file field - the command must contain a "[input_file_path]"
        current_command = current_command.replace("[input_file_path]", f"\"{input_file_path}\"")

        # Replace the output file field - the command must contain a "[output_file_path]"
        current_command = current_command.replace("[output_file_path]", f"\"{output_file_path}\"")

        # Run and save the process handle
        # Grab any empty slot and assign a task to it

        # Use temporary slots, so if the subprocess raises an error, we can restore the state
        # If we don't do that, it might leave the provider in an inconsistent state
        empty_slot = self.task_empty_slot.pop()
        task = None

        try:
            task = Task(current_command, retry_limit, {"input_file": input_file_path, "output_file": output_file_path})

        except Exception as e:
            # Restore the state
            # Return the empty store back
            self.task_empty_slot.add(empty_slot)
            print(e, file=sys.stderr)
            raise e

        # All good
        self.task_handles[ empty_slot ] = task

    # Check if any task has:
    # - completed;
    # - need retries; or
    # - failed.
    # And return these results
    def get_tasks_results(self):

        tasks_info = []

        for idx, task in enumerate(self.task_handles):

            # There is no task here
            if task == None:
                continue

            # Did it finish?
            if task.poll() == None:
                # It did not
                continue

            # Did it finish with an error?
            if task.poll() != 0:

                # Yeah, but it errored
                # Can we retry?
                if task.can_retry():
                    # Yes, then retry
                    task.retry()
                    tasks_info.append( TaskResult(TaskSatus.RETRY, None, task.data()) )
                    continue

                # We can't retry anymore
                else:

                    # Free the slot
                    self.task_handles[idx] = None
                    self.task_empty_slot.add(idx)

                    tasks_info.append( TaskResult(TaskSatus.FAIL, task.poll(), task.data()) )
                    continue

            # Did it finish successfully?
            if task.poll() == 0:

                # Free the slot
                self.task_handles[idx] = None
                self.task_empty_slot.add(idx)

                tasks_info.append( TaskResult(TaskSatus.SUCESS, task.poll(), task.data()) )
                continue

        return tasks_info

    # Check if the execution limits were hit
    def has_capacity(self):

        if len(self.task_handles)-len(self.task_empty_slot) < self.execution_limit:
            return True

        return False

