"""Interfaces to automatic source code formatting tools."""

from . import file_operation, task_utilities
from pathlib import Path
from typing import List, Optional

MAX_CODE_LINE_WIDTH = 120


def format_py(
    search_path: Optional[Path] = None,
    individual_files: Optional[List[Path]] = None,
    exclude_paths: Optional[List[Path]] = None,
    exclude_files: Optional[List[Path]] = None,
    check: bool = False,
):
    """
    Format Python code.

    Args:
        search_path:      Path to search for .py files to format.
        individual_files: List of specific files to include.
        exclude_paths:    List of paths to exclude - all code within these paths will be ignored.
        exclude_files:    List of specific files to exclude.
        check:            If True, check for formatting conformance but do not modify any files.

    """
    format_black(
        search_path=search_path,
        individual_files=individual_files,
        exclude_paths=exclude_paths,
        exclude_files=exclude_files,
        check=check,
    )
    format_docformatter(
        search_path=search_path,
        individual_files=individual_files,
        exclude_paths=exclude_paths,
        exclude_files=exclude_files,
        check=check,
    )
    format_isort(
        search_path=search_path,
        individual_files=individual_files,
        exclude_paths=exclude_paths,
        exclude_files=exclude_files,
        check=check,
    )


def format_black(
    search_path: Optional[Path] = None,
    individual_files: Optional[List[Path]] = None,
    exclude_paths: Optional[List[Path]] = None,
    exclude_files: Optional[List[Path]] = None,
    check: bool = False,
):
    """
    Format Python code using black.

    Args:
        search_path:      Path to search for .py files to format.
        individual_files: List of specific files to include.
        exclude_paths:    List of paths to exclude - all code within these paths will be ignored.
        exclude_files:    List of specific files to exclude.
        check:            If True, check for formatting conformance but do not modify any files.

    """
    task_utilities.print_minor_banner("Formatting Python Using black")

    python_files = file_operation.get_python_source_list(
        search_path=search_path,
        individual_files=individual_files,
        exclude_paths=exclude_paths,
        exclude_files=exclude_files,
    )
    files_string = " ".join([x.as_posix() for x in python_files])
    extra_args = "--check" if check else ""

    task_utilities.execute_command(f"black --config coding_standard/pyproject.toml {extra_args} {files_string}")


def format_docformatter(
    search_path: Optional[Path] = None,
    individual_files: Optional[List[Path]] = None,
    exclude_paths: Optional[List[Path]] = None,
    exclude_files: Optional[List[Path]] = None,
    check: bool = False,
):
    """
    Format Python code using docformatter.

    Args:
        search_path:      Path to search for .py files to format.
        individual_files: List of specific files to include.
        exclude_paths:    List of paths to exclude - all code within these paths will be ignored.
        exclude_files:    List of specific files to exclude.
        check:            If True, check for formatting conformance but do not modify any files.

    """
    task_utilities.print_minor_banner("Formatting Python Using docformatter")

    python_files = file_operation.get_python_source_list(
        search_path=search_path,
        individual_files=individual_files,
        exclude_paths=exclude_paths,
        exclude_files=exclude_files,
    )
    files_string = " ".join([x.as_posix() for x in python_files])
    extra_args = "--check" if check else "--in-place"

    task_utilities.execute_command(
        f"docformatter --config coding_standard/pyproject.toml --pre-summary-newline {extra_args} {files_string}"
    )


def format_isort(
    search_path: Optional[Path] = None,
    individual_files: Optional[List[Path]] = None,
    exclude_paths: Optional[List[Path]] = None,
    exclude_files: Optional[List[Path]] = None,
    check: bool = False,
):
    """
    Format Python code using docformatter.

    Args:
        search_path:      Path to search for .py files to format.
        individual_files: List of specific files to include.
        exclude_paths:    List of paths to exclude - all code within these paths will be ignored.
        exclude_files:    List of specific files to exclude.
        check:            If True, check for formatting conformance but do not modify any files.

    """
    task_utilities.print_minor_banner("Formatting Python Using isort")

    python_files = file_operation.get_python_source_list(
        search_path=search_path,
        individual_files=individual_files,
        exclude_paths=exclude_paths,
        exclude_files=exclude_files,
    )
    files_string = " ".join([x.as_posix() for x in python_files])
    extra_args = "--check-only" if check else ""

    task_utilities.execute_command(f"isort --settings-file coding_standard/pyproject.toml {extra_args} {files_string}")
