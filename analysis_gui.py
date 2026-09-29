"""OPAL-OKB — Compatibility shim for the analysis GUI package.

All widget classes and the :class:`AnalysisPanel` orchestrator have been
moved to the :mod:`gui` package.  This module re-exports them so that
existing imports such as ``from analysis_gui import AnalysisPanel``
continue to work unchanged.
"""

# Public API re-exported from the gui package
from gui.analysis_panel import AnalysisPanel
from gui.analysis_pipeline import compute_all_analysis
from gui.widgets import (
    # Base
    InteractivePlot,
    AberrationPlotWidget,
    make_table,
    clear_layout,
    wl_to_plot_color,
    # Spot diagram family
    SpotDiagramWidget,
    HeatmapWidget,
    FocusDiagramWidget,
    # Aberration graphs
    AberrationGraphWidget,
    DistortionWidget,
    AstigmatismWidget,
    ComaWidget,
    # MTF
    MTFWidget,
    # PSF family
    PSFWidget,
    LSFWidget,
    ENCWidget,
    PTFWidget,
    ESFWidget,
    PSF3DWidget,
    # Wavefront
    WavefrontMapWidget,
    ZernikeWidget,
    WfRmsFieldMplWidget,
    # Other widgets
    FocusCurveWidget,
    ChiefRayWidget,
    BeamGeometryWidget,
    BarTargetWidget,
)

__all__ = [
    'AnalysisPanel',
    'compute_all_analysis',
    'InteractivePlot',
    'AberrationPlotWidget',
    'make_table',
    'clear_layout',
    'wl_to_plot_color',
    'SpotDiagramWidget',
    'HeatmapWidget',
    'FocusDiagramWidget',
    'AberrationGraphWidget',
    'DistortionWidget',
    'AstigmatismWidget',
    'ComaWidget',
    'MTFWidget',
    'PSFWidget',
    'LSFWidget',
    'ENCWidget',
    'PTFWidget',
    'ESFWidget',
    'PSF3DWidget',
    'WavefrontMapWidget',
    'ZernikeWidget',
    'WfRmsFieldMplWidget',
    'FocusCurveWidget',
    'ChiefRayWidget',
    'BeamGeometryWidget',
    'BarTargetWidget',
]
