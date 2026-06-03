# Copyright © 2026, UChicago Argonne, LLC
# See LICENSE for terms and disclaimer.

"""Console-private plot rendering layer.

Consumes adapt.consumers.analysis result objects and writes PNG/MP4 files.
Zero GUI imports — all rendering uses matplotlib Agg/FFMpeg backends.
"""

from adapt.consumers.console.plots.registry import FigureTypeRegistry, RegistrationError

__all__ = ["FigureTypeRegistry", "RegistrationError"]
