"""
Buzzer detection package: audio I/O, signal-processing detection, plotting, and Tk GUI.

The public API is intentionally small. Application code that does not need the GUI should depend on
``analysis.AnalysisService`` and the dataclasses in ``analysis``; the ``gui`` module is for the Tk front-end only.

"""

from buzzer.analysis import AnalysisConfig, AnalysisResult, AnalysisService

__all__ = ["AnalysisConfig", "AnalysisResult", "AnalysisService"]
