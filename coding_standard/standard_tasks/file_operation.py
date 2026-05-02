"""Interfaces to retrieve file lists."""

from pathlib import Path
from typing import List, Optional


def get_python_source_list(
    search_path: Optional[Path] = None,
    individual_files: Optional[List[Path]] = None,
    exclude_paths: Optional[List[Path]] = None,
    exclude_files: Optional[List[Path]] = None,
) -> List[Path]:
    """
    Get python source list.

    Args:
        search_path:                Path to search for python files to format.
        individual_files:           List of specific files to include.
        exclude_paths:              List of paths to exclude - all code within these paths will be ignored.
        exclude_files:              List of specific files to exclude.

    Returns:
        A list of python source files.

    """
    default_exclude_directories = [
        Path(".git").absolute(),
        Path(".vscode").absolute(),
        Path("venv").absolute(),
        Path(".venv").absolute(),
    ]

    return get_source_list(
        file_patterns=["**/*.py"],
        search_path=search_path,
        individual_files=individual_files,
        default_exclude_paths=default_exclude_directories,
        exclude_paths=exclude_paths,
        exclude_files=exclude_files,
    )


# pylint: disable=R0913,R0917
#  too-many-arguments, too-many-positional-arguments
def get_source_list(
    file_patterns: List[str],
    search_path: Optional[Path] = None,
    individual_files: Optional[List[Path]] = None,
    default_exclude_paths: Optional[List[Path]] = None,
    exclude_paths: Optional[List[Path]] = None,
    exclude_files: Optional[List[Path]] = None,
) -> List[Path]:
    """
    Get source list.

    Args:
        file_patterns:              File patterns that are interested.
        search_path:                Path to search for files to format.
        individual_files:           List of specific files to include.
        default_exclude_paths:      List of specific paths to exclude
        exclude_paths:              List of paths to exclude - all code within these paths will be ignored.
        exclude_files:              List of specific files to exclude.

    Returns:
        A list of python source files.

    """
    exclude_directories = _create_exclude_paths_list(
        default_exclude_paths=default_exclude_paths, exclude_paths=exclude_paths
    )

    if exclude_files is None:
        exclude_files = []

    all_files: List[Path] = []
    if search_path is not None:
        for file_pattern in file_patterns:
            all_files.extend(list(search_path.glob(file_pattern)))

    if individual_files is not None:
        all_files.extend(individual_files)

    files: List[Path] = []
    for file in all_files:
        exclude = False
        for exclude_directory in exclude_directories:
            if file.absolute().as_posix().startswith(exclude_directory.absolute().as_posix()):
                exclude = True
                break
        for exclude_file in exclude_files:
            if file.absolute().as_posix() == exclude_file.absolute().as_posix():
                exclude = True
                break
        if not exclude:
            files.append(file)
    return files


def _create_exclude_paths_list(
    default_exclude_paths: Optional[List[Path]] = None,
    exclude_paths: Optional[List[Path]] = None,
) -> List[Path]:
    """
    Combine exclude paths and default exclude paths into one list.

    Args:
        default_exclude_paths:      List of specific paths to exclude
        exclude_paths:              List of paths to exclude - all code within these paths will be ignored.

    Returns:
        List of paths to be excluded.

    """
    if exclude_paths is None:
        if default_exclude_paths is None:
            exclude_directories = []
        else:
            exclude_directories = default_exclude_paths
    else:
        exclude_directories = exclude_paths
        if default_exclude_paths is not None:
            for default_exclude_path in default_exclude_paths:
                if default_exclude_path not in exclude_directories:
                    exclude_directories.append(default_exclude_path)
    return exclude_directories
