"""Interface to python unit-test tools."""

import sys
from . import file_operation, task_utilities
from pathlib import Path
from typing import List, Optional


def _prepare_directory(path: Path) -> None:
    """Ensure that directory exists."""
    # Create target Directory if don't exist
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)


def test_py(
    search_path: Path,
    output_path: Path,
    exclude_paths: Optional[List[Path]] = None,
    exclude_files: Optional[List[Path]] = None,
    test_expression: str = "",
) -> None:
    """
    Test Python files.

    Args:
        search_path:    Path to search for python file to lint.
        output_path:    Path to output lint file.
        exclude_paths:  List of paths to exclude - all code within these paths will be ignored.
        exclude_files:  List of specific files to exclude.
        test_expression: A specific test to be tested.

    Returns:
        None:

    """
    files = file_operation.get_python_source_list(
        search_path=search_path,
        individual_files=None,
        exclude_paths=exclude_paths,
        exclude_files=exclude_files,
    )

    files_as_string = ""
    for file in files:
        files_as_string += f"{file.as_posix()} "

    extra_args = f"-k {test_expression} " if test_expression != "" else " "
    extra_args += "--color=no"

    junit_xml = output_path / "pytest.xml"
    html = output_path / "html_pytest" / "pytest.html"
    html_coverage_path = output_path / "coverage" / "html_coverage"
    xml_coverage_path = output_path / "coverage" / "coverage.xml"

    _prepare_directory(output_path)

    python_cmd = "python3 -m" if sys.platform.lower() == "linux" else ""

    task_utilities.execute_command(
        f"{python_cmd} pytest --config-file setup.cfg --cov --cov-report term "
        f"--cov-report=html:{html_coverage_path.as_posix()} "
        f"--cov-report=xml:{xml_coverage_path.as_posix()} -ra "
        f"--junitxml={junit_xml.as_posix()} "
        f"--html={html.as_posix()} "
        f"{extra_args} {files_as_string}"
    )
