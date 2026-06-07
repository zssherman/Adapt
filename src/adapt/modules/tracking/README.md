# Storm Cell Tracking Module

**Author**: Adapt Development Team
**Status**: Production-ready
**Module Name**: `tracking`

## Overview

The tracking module performs tracking-only association of segmented radar cells across consecutive scans using projected mask overlap and a multi-term matching cost. It emits scan-local tracking observations, explicit lineage events, and same-scan adjacency translated into track identity space.

## Features

- **Optical Flow-Based Prediction**: Uses projected cell masks for robust matching
- **Multi-Term Cost Function**: Combines position, IoU, area, and reflectivity
- **Graph-Based Lineage**: Stores complete tracking history as a directed graph
- **Explicit Events**: Emits CONTINUE, SPLIT, MERGE, INITIATION, TERMINATION event rows per scan
- **Adjacency Plumbing**: Translates scan-local cell adjacency into track identity space

## Architecture

```
┌──────────────────────────┐
│  RadarCellTracker        │  Scientific Implementation
│  - Tracking graph        │
│  - Cost function         │
│  - Hungarian assignment  │
│  - Event emission        │
└──────────────────────────┘
            ↓
┌──────────────────────────┐
│  TrackingModule          │  Pipeline Integration
│  - BaseModule wrapper    │
│  - Context management    │
│  - Contract validation   │
└──────────────────────────┘
```

## Usage

### As Part of Pipeline

```python
# Automatic via pipeline DAG
# tracking module runs after projection module

# Context inputs:
#   - projected_ds: xr.Dataset (from ProjectionModule)
#   - cell_stats: pd.DataFrame (from AnalysisModule)
#   - cell_adjacency: pd.DataFrame (from AnalysisModule)
#   - config: InternalConfig
#
# Context outputs:
#   - tracked_cells: pd.DataFrame
#   - track_events: pd.DataFrame
#   - tracked_cell_adjacency: pd.DataFrame
```

### Standalone

```python
from adapt.modules.tracking.module import RadarCellTracker
from adapt.schemas import init_runtime_config

# Initialize
config = init_runtime_config(user_config)
tracker = RadarCellTracker(config)

# Track one scan at a time (scan-local outputs)
tracked_cells, track_events, tracked_cell_adjacency = tracker.track(ds, cell_stats, cell_adjacency)

# Access results
print(f"Tracked {len(tracks_df)} distinct storms")
print(f"Total {len(cells_df)} cell observations")
```

## Configuration

Default configuration in `adapt.schemas.param.TrackerConfig`:

```python
max_cost_threshold: float = 0.7         # Maximum cost for valid assignment
merge_memory_scans: int = 3             # Scans to remember for merge tracking
core_reflectivity_threshold: float = 40.0  # Core area threshold (dBZ)
```

Override in user config:

```yaml
tracker:
  max_cost_threshold: 0.65
  merge_memory_scans: 5
  core_reflectivity_threshold: 42.0
```

## Data Outputs

### Tracked Cells

One row per tracked cell observation in the current scan:

| Column | Type | Description |
|--------|------|-------------|
| `time` | datetime64 | Observation timestamp |
| `track_index` | int | Deterministic track index (starts at 1) |
| `track_id` | str | Deterministic UUID (derived from run_id + track_index) |
| `cell_label` | int | Cell label from segmentation |
| `area` | float | Cell area (km²) |
| `centroid_x`, `centroid_y` | float | Cell center coordinates |
| `mean_reflectivity` | float | Average dBZ |
| `max_reflectivity` | float | Peak dBZ |
| `core_area` | float | Area above core threshold (km²) |
| `n_connected_cells` | int | Number of adjacent tracked neighbors in this scan |
| `connected_track_ids_json` | str | JSON list of adjacent `track_id` values |

### Track Events

Explicit lineage/event rows for the current scan:

| Column | Type | Description |
|--------|------|-------------|
| `time` | datetime64 | Scan timestamp |
| `event_type` | str | CONTINUE \| SPLIT \| MERGE \| INITIATION \| TERMINATION |
| `source_track_id` | str or None | Source track (if applicable) |
| `target_track_id` | str or None | Target track (if applicable) |
| `cost` | float or None | Matching cost (CONTINUE only in v1) |

### Tracked Cell Adjacency

Normalized adjacency pairs in track identity space:

| Column | Type | Description |
|--------|------|-------------|
| `time` | datetime64 | Scan timestamp |
| `track_id_a`, `track_id_b` | str | Adjacent tracks in this scan |
| `touching_boundary_pixels` | int | Boundary-touch count from analysis |

## Algorithm Details

### Cost Function

The matching cost combines multiple terms:

```
cost = 0.4 * D_pos + 0.3 * (1 - IoU) + 0.15 * |log(A2/A1)| + 0.1 * |Z2 - Z1| + 0.05 * core_penalty
```

Where:
- `D_pos`: Normalized centroid distance
- `IoU`: Intersection-over-union of masks
- `A2/A1`: Area ratio
- `Z2 - Z1`: Reflectivity difference

### Assignment

Uses the Hungarian algorithm (`scipy.optimize.linear_sum_assignment`) to find optimal cell-to-cell assignments while minimizing total cost.

### Search Region

Candidates are filtered by non-zero overlap with the projected previous-cell labels in the current scan coordinates (`cell_projections[0]`).

## Testing

Run behavior-driven tests:

```bash
pytest tests/modules/tracking/ -v
```

Tests cover:
- Linear motion tracking
- Cell growth and decay
- New cell birth and death
- Crossing tracks
- Graph structure
- Cost function
- DataFrame outputs

All tests use synthetic data for reproducibility.

## Dependencies

- `numpy`: Array operations
- `pandas`: DataFrame outputs
- `xarray`: Dataset handling
- `scipy`: Hungarian assignment
- `networkx`: Tracking graph storage

## Performance

Typical performance for 50 cells per scan:
- **Tracking time**: 10-50 ms per frame pair
- **Memory usage**: ~10 MB for 100 scans
- **Graph size**: Linear with total cell-observations

## Future Enhancements

Potential improvements identified during development:

1. **Advanced Split/Merge Logic**: Implement temporary merge identity restoration
2. **Multi-Step Prediction**: Use multiple projection steps for better matching
3. **Track Smoothing**: Apply Kalman filtering to motion vectors
4. **Parallel Processing**: Process multiple files concurrently
5. **Persistence**: Save/load tracking graph for resumable processing

## References

- **Hungarian Algorithm**: Kuhn, H. W. (1955). "The Hungarian method for the assignment problem"
- **Storm Tracking**: Dixon & Wiener (1993). "TITAN: Thunderstorm Identification, Tracking, Analysis, and Nowcasting"
- **Optical Flow**: Farnebäck, G. (2003). "Two-Frame Motion Estimation Based on Polynomial Expansion"

## Developer Notes

This module was implemented as the **first additional default module** in the Adapt system. For detailed developer experience and implementation patterns, see `MODULE_EXTENSION_GUIDE.md` in the repository root.

Key learnings:
- The two-layer pattern (scientific class + wrapper) works extremely well
- Pydantic config schemas eliminate runtime validation complexity
- Contract validators provide fail-fast guarantees
- Behavior-driven tests with synthetic data are robust and fast

## License

Same as Adapt main project.

## Contact

For questions or issues, open a GitHub issue in the Adapt repository.
