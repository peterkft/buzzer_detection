"""Utilities and helper functions to assist with task execution and reporting."""

import shlex
import shutil
import subprocess
import sys
import time
import traceback
from types import TracebackType
from typing import Optional, Type

CONSOLE_OUTPUT_WIDTH = 77
CONSOLE_OUTPUT_HEIGHT = 24


class CommandFailed(Exception):
    """Raised when command excutred thought task utilities failed."""

    def __init__(self, command: str, working_directory: Optional[str], return_code: int):
        self.command = command
        self.return_code = return_code
        self.working_directory = working_directory


def print_major_banner(string: str) -> None:
    """
    Print an obvious banner.

    Use this to indicate the start of a task.

    """
    columns = shutil.get_terminal_size(fallback=(CONSOLE_OUTPUT_WIDTH, CONSOLE_OUTPUT_HEIGHT)).columns
    print("#" * columns)

    if len(string) <= columns - 2:
        padding = (columns - 2) - len(string)
        l_padding = int(padding / 2)
        r_padding = padding - l_padding
        print("#" + " " * l_padding + string + " " * r_padding + "#")
    else:
        print("#" + string + "#")

    print("#" * columns)


def print_minor_banner(string: str) -> None:
    """
    Print a less obvious banner.

    Use this to indicate the start of major steps within a task.

    """
    columns = shutil.get_terminal_size(fallback=(CONSOLE_OUTPUT_WIDTH, CONSOLE_OUTPUT_HEIGHT)).columns

    print("*" * columns)

    if len(string) <= columns - 2:
        padding = (columns - 2) - len(string)
        l_padding = int(padding / 2)
        r_padding = padding - l_padding
        print("*" + " " * l_padding + string + " " * r_padding + "*")
    else:
        print("*" + string + "*")

    print("*" * columns)


def print_separator() -> None:
    """
    Print a separator to help separate output/operations.

    Use this to separate individual operations within a task.

    """
    columns = shutil.get_terminal_size(fallback=(CONSOLE_OUTPUT_WIDTH, CONSOLE_OUTPUT_HEIGHT)).columns
    print("-" * columns)


def execute_command(command: str, working_directory: Optional[str] = None, shell: bool = False) -> None:
    """Execute the given command."""
    print_separator()
    print(f"> {command}")
    try:
        with subprocess.Popen(shlex.split(command), shell=shell, cwd=working_directory) as p:
            p.wait()
            p.communicate()
            return_code = p.returncode
    except FileNotFoundError as ex:
        print(f"\n ERROR: COMMAND NOT FOUND: {ex}")
        if working_directory:
            print(f"  Working Directory: {working_directory}")
        print(f"  Command: {command}")
        raise

    if return_code != 0:
        print("\n ERROR: COMMAND FAILED:")
        if working_directory:
            print(f"  Working Directory: {working_directory}")
        print(f"  Command: {command}")
        print(f"  Return Code: {return_code}")
        raise CommandFailed(command, working_directory, return_code)
    print_separator()
    print("")


class TaskContext:
    """Assists with output formatting, error reporting and execution of commands within an invoke task."""

    def __init__(self, task_name: str) -> None:
        self.task_name = task_name
        self.start_time = 0.0
        self.end_time = 0.0

    def __enter__(self) -> "TaskContext":
        print_major_banner(f"{self.task_name}")
        self.start_time = time.time()
        return self

    def __exit__(
        self,
        exception_type: Optional[Type[BaseException]],
        exception_value: Optional[BaseException],
        exception_traceback: Optional[TracebackType],
    ) -> bool:
        self.end_time = time.time()
        try:
            if exception_type is not None:
                if exception_type is KeyboardInterrupt:
                    print("Terminated")
                    return False
                if isinstance(exception_value, CommandFailed):
                    sys.exit(exception_value.return_code)
                elif exception_type is not None:
                    traceback.print_exception(exception_type, exception_value, exception_traceback)
                    sys.exit(1)
            return True
        finally:
            columns = shutil.get_terminal_size(fallback=(CONSOLE_OUTPUT_WIDTH, CONSOLE_OUTPUT_HEIGHT)).columns
            print("-" * columns)
            print(f'Task "{self.task_name}" completed')

            duration = self.end_time - self.start_time
            milliseconds = (duration % 1) * 1000
            minutes, seconds = divmod(duration, 60)
            print(f"Duration:   {minutes:2.0f}:{seconds:02.0f}.{milliseconds:03.0f}")
            print("Task result: " + ("Successful" if exception_type is None else "ERROR"))
