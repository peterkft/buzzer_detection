"""Provides tasks for pyinvoke."""

import os
import shutil
from coding_standard.standard_tasks import code_formatting, lint, task_utilities
from invoke import task
from pathlib import Path

# Directory where output artifacts will be generated/stored.
OUTPUT_DIRECTORY = Path("output").absolute()
SOURCE_DIRECTORY = Path("source").absolute()

# Directories which do not contain our source code and should be excluded from all static analysis.
EXCLUDE_DIRECTORIES = [
    Path(".idea").absolute(),
    Path(".venv").absolute(),
    Path("output").absolute(),
    Path("venv").absolute(),
]


def _prepare_output_directory() -> None:
    """Ensure that the output directory exists."""
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)


@task(aliases=["c"])
def clean(context):  # pylint: disable=unused-argument
    """Clean all build artifacts."""
    with task_utilities.TaskContext("Clean"):
        if Path.exists(OUTPUT_DIRECTORY):
            shutil.rmtree(OUTPUT_DIRECTORY)


@task(aliases=["f", "format"])
def format_all(context, check=False):  # pylint: disable=unused-argument
    """
    Run all code formatting tools.

    Args:
        context: Context
        check:  If True, check that formatting is correct without making any file changes.

    """
    with task_utilities.TaskContext("Format"):
        code_formatting.format_py(search_path=Path().absolute(), exclude_paths=EXCLUDE_DIRECTORIES, check=check)


@task(aliases=["l", "lint"])
def lint_all(context):  # pylint: disable=unused-argument
    """Execute all linting tools."""
    with task_utilities.TaskContext("Lint"):
        lint.lint_py(search_path=Path().absolute(), output_path=OUTPUT_DIRECTORY, exclude_paths=EXCLUDE_DIRECTORIES)


@task(aliases=["exe"])
def executable(context):  # pylint: disable=unused-argument
    """Compile the project into an executable program."""
    with task_utilities.TaskContext("Compile Executable"):
        exe_path = OUTPUT_DIRECTORY / "installer"
        source_script = "buzzer_gui.py"

        path = Path(SOURCE_DIRECTORY)
        os.chdir(path)
        # distpath, workpath, and specpath must be different directories: PyInstaller wipes the workpath
        # mid-build and would otherwise delete artifacts the dist/spec steps still need.
        work_path = exe_path / "_build"
        icon_path = SOURCE_DIRECTORY / "icon" / "buzzer.ico"
        task_utilities.execute_command(
            f"""pyinstaller {source_script} --onefile --windowed --noconfirm --name BuzzerDetector
                --icon {icon_path.as_posix()}
                --distpath {exe_path.as_posix()} --workpath {work_path.as_posix()}
                --specpath {exe_path.as_posix()}"""
        )
