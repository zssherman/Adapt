# Copyright © 2026, UChicago Argonne, LLC
# See LICENSE for terms and disclaimer.

"""Detection module config schema.

Holds exactly the fields RadarCellSegmenter consumes. Built once at startup by
DetectModule.build_config() from the resolved InternalConfig. Frozen.
"""

from pydantic import BaseModel, ConfigDict


class DetectionConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    method: str
    threshold: float
    closing_kernel: tuple[int, int]
    filter_by_size: bool
    min_cellsize_gridpoint: int
    max_cellsize_gridpoint: int | None
    h_maxima: float
    reflectivity_var: str
    labels_var: str
    z_level: float
