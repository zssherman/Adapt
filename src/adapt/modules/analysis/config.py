# Copyright © 2026, UChicago Argonne, LLC
# See LICENSE for terms and disclaimer.

"""Analysis module config schema.

Holds exactly the fields RadarCellAnalyzer consumes. Built once at startup by
AnalysisModule.build_config() from the resolved InternalConfig. Frozen.

Note: max_projection_steps is a cross-reference to the projector section —
the analyzer needs to know how many projection frames exist.
"""

from pydantic import BaseModel, ConfigDict


class AnalysisConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    radar_variables: tuple
    exclude_fields: tuple
    adjacency_min_touching: int
    max_projection_steps: int
    reflectivity_var: str
    labels_var: str
    z_level: float
