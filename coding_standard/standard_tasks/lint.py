"""Interfaces to linting/static analysis tools."""

from . import file_operation, task_utilities
from pathlib import Path
from typing import List, Optional

MAX_CODE_LINE_WIDTH = 120


class LintError(Exception):
    """Exception class from Lint check."""


def _prepare_directory(path: Path) -> None:
    """Ensure that directory exists."""
    # Create target Directory if don't exist
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)


def lint_py(
    search_path: Path,
    output_path: Path,
    exclude_paths: Optional[List[Path]] = None,
    exclude_files: Optional[List[Path]] = None,
) -> None:
    """
    Lint all Python files.

    Args:
        search_path:    Path to search for python file to lint.
        output_path:    Path to output lint file.
        exclude_paths:  List of paths to exclude - all code within these paths will be ignored.
        exclude_files:  List of specific files to exclude.

    Returns:
        None:

    """
    lint_flake8(output_path=output_path)
    lint_pylint(search_path=search_path, exclude_paths=exclude_paths, exclude_files=exclude_files)
    lint_mypy(output_path=output_path)


def lint_flake8(output_path: Path) -> None:
    """
    Lint all Python files using flake8.

    Args:
        output_path:    Path to output lint file.

    Returns:
        None:

    """
    task_utilities.print_minor_banner("Linting Python using flake8")

    _prepare_directory(output_path)
    output_file = output_path / "flake8" / "flake8.txt"

    task_utilities.execute_command(f"flake8 --config=setup.cfg --benchmark --output-file={output_file.as_posix()}")


def lint_pylint(
    search_path: Path,
    exclude_paths: Optional[List[Path]] = None,
    exclude_files: Optional[List[Path]] = None,
) -> None:
    """
    Lint all Python files using pylint.

    Args:
        search_path:    Path to search for python file to lint.
        exclude_paths:  List of paths to exclude - all code within these paths will be ignored.
        exclude_files:  List of specific files to exclude.

    Returns:
        None:

    """
    task_utilities.print_minor_banner("Linting Python using pylint")

    python_files = file_operation.get_python_source_list(
        search_path=search_path,
        individual_files=None,
        exclude_paths=exclude_paths,
        exclude_files=exclude_files,
    )

    python_files_as_string = ""
    for python_file in python_files:
        python_files_as_string += f"{python_file.as_posix()} "

    task_utilities.execute_command(f"pylint --rcfile=setup.cfg {python_files_as_string}")


def lint_mypy(output_path: Path) -> None:
    """
    Lint all Python files using mypy.

    Args:
        output_path:    Path to output lint file.

    Returns:
        None:

    """
    task_utilities.print_minor_banner("Linting Python using mypy")

    output_mypy_path = output_path / "mypy"
    html_path = output_mypy_path / "html"

    _prepare_directory(output_path)
    _prepare_directory(output_mypy_path)
    output_xml_file = output_mypy_path / "mypy.xml"

    task_utilities.execute_command(
        f"mypy --html-report {html_path.as_posix()} --junit-xml {output_xml_file.as_posix()} ."
    )
