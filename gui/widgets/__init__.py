"""GUI analysis widgets package — re-exports all widget classes.

Import from here for backward compatibility::

    from gui.widgets import SpotDiagramWidget, MTFWidget, AnalysisPanel
"""

from .base import (
    InteractivePlot,
    AberrationPlotWidget,
    make_table,
    clear_layout,
    wl_to_plot_color,
)
from .spot_diagram import (
    SpotDiagramWidget,
    HeatmapWidget,
    FocusDiagramWidget,
)
from .aberration_graphs import (
    AberrationGraphWidget,
    DistortionWidget,
    AstigmatismWidget,
    ComaWidget,
)
from .mtf_widgets import MTFWidget
from .psf_widgets import (
    PSFWidget,
    LSFWidget,
    ENCWidget,
    PTFWidget,
    ESFWidget,
    PSF3DWidget,
)
from .wavefront import (
    WavefrontMapWidget,
    ZernikeWidget,
    WavefrontRmsVsFieldWidget,
)
from .focus_curve import FocusCurveWidget
from .chief_ray import ChiefRayWidget
from .beam_geometry import BeamGeometryWidget
from .bar_target import BarTargetWidget

__all__ = [
    # Base
    'InteractivePlot',
    'AberrationPlotWidget',
    'make_table',
    'clear_layout',
    'wl_to_plot_color',
    # Spot
    'SpotDiagramWidget',
    'HeatmapWidget',
    'FocusDiagramWidget',
    # Aberration graphs
    'AberrationGraphWidget',
    'DistortionWidget',
    'AstigmatismWidget',
    'ComaWidget',
    # MTF
    'MTFWidget',
    # PSF family
    'PSFWidget',
    'LSFWidget',
    'ENCWidget',
    'PTFWidget',
    'ESFWidget',
    'PSF3DWidget',
    # Wavefront
    'WavefrontMapWidget',
    'ZernikeWidget',
    'WavefrontRmsVsFieldWidget',
    # Other
    'FocusCurveWidget',
    'ChiefRayWidget',
    'BeamGeometryWidget',
    'BarTargetWidget',
]
