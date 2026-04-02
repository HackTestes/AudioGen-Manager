from abc import ABC, abstractmethod
import shlex, subprocess
import sys
import pathlib

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
    def __init__(self, status, return_code, task, exception=None):
        self.status = status
        self.return_code = return_code
        self.task = task
        self.exception = exception

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

def command_replacement(command: str, input_file_path: str):

    # Support for the following replacements
    # [input_file_path]: full path to the input file
    # [input_file_name]: the file name without the path
    # [input_file_stem]: just the file "name" without the extension (pathlib stem)
    # [input_file_parent]: the path leading the the folder containing the file
    command = command.replace("[input_file_path]", f"{pathlib.Path(input_file_path).as_posix()}")
    command = command.replace("[input_file_name]", f"{str( pathlib.Path(input_file_path).name )}")
    command = command.replace("[input_file_stem]", f"{str( pathlib.Path(input_file_path).stem )}")
    command = command.replace("[input_file_parent]", f"{str( pathlib.Path(input_file_path).parent.as_posix() )}")

    return command

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
        self.task_handles = [None]*execution_limit # Represents an empty task slot
        self.task_empty_slot = set( range(0, execution_limit) ) # Represents the indexes of empty slots

    # Grab any empty slot and assign a task to it
    def add_task(self, task):
        empty_slot = self.task_empty_slot.pop()
        self.task_handles[ empty_slot ] = task

    def free_task(self, task_idx):
        self.task_empty_slot.add(task_idx)
        self.task_handles[task_idx] = None

    # Adds a task to be executed by the provider
    def run_task(self, input_file_path, lang, retry_limit):

        if lang not in self.commands:
            raise AudioProvider_LanguageNotSupported()

        if not self.has_capacity():
            raise AudioProvider_NoCapacityLeft()

        current_command = self.commands[lang]

        # Make the necessary ajustments to the command string
        current_command = command_replacement(current_command, input_file_path)

        task = Task(current_command, retry_limit, {"input_file": input_file_path})

        # We only assign the task after opening the process,
        # so we don't leave the obj in an inconsistent state if it errors
        self.add_task(task)

        # Retrun the command used so it can easier for testing and to report back to the user what is hapenning
        return current_command

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
                    try:
                        task.retry()
                        tasks_info.append( TaskResult(TaskSatus.RETRY, task.poll(), task) )
                    
                    # An error occurred dung the retry (in a new popen call)
                    # Consider the task as failed
                    # Why catch almost everything? I want the program to process as much as possible without human intervention
                    # And exception could cause the process to close. So it is preferable to just get the error and continue on
                    except Exception as e:
                        self.free_task(idx)
                        # Since the process couldn't even be created, it wasn't able to return eny code, so "None"
                        tasks_info.append( TaskResult(TaskSatus.FAIL, None, task, e) )
                    continue

                # We can't retry anymore
                else:

                    # Free the slot
                    self.free_task(idx)

                    tasks_info.append( TaskResult(TaskSatus.FAIL, task.poll(), task) )
                    continue

            # Did it finish successfully?
            if task.poll() == 0:

                # Free the slot
                self.free_task(idx)

                tasks_info.append( TaskResult(TaskSatus.SUCCESS, task.poll(), task) )
                continue

        return tasks_info

    # Check if the execution limits were hit
    def has_capacity(self):

        if len(self.task_handles)-len(self.task_empty_slot) < self.execution_limit:
            return True

        return False

