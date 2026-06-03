# Copyright © 2026, UChicago Argonne, LLC
# See LICENSE for terms and disclaimer.

"""RecipeExecutor — renders FigureRecipe / MovieRecipe via console.plots."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from adapt.consumers.console.workspace.models import FigureRecipe

__all__ = ["RecipeExecutor"]

_FIGURE_DISPATCH: dict[str, str] = {
    "population_histogram": "histogram",
    "population_scatter": "scatter",
    "lifecycle_composite": "composite",
    "lifecycle_heatmap": "heatmap",
}


class RecipeExecutor:
    """Renders FigureRecipe objects to PNG files via the console.plots layer."""

    def render_figure(
        self,
        recipe: FigureRecipe,
        workspace,
        client,
    ) -> Path:
        """Render *recipe* and persist it to the workspace figures directory.

        Parameters
        ----------
        recipe:
            Configured FigureRecipe.
        workspace:
            Open WorkspaceManager instance.
        client:
            RepositoryClient used to fetch track data.

        Returns
        -------
        Path
            Path to the rendered PNG file.

        Raises
        ------
        KeyError
            If ``recipe.figure_type`` is not a known type.
        """
        if recipe.figure_type not in _FIGURE_DISPATCH:
            raise KeyError(
                f"Unknown figure type '{recipe.figure_type}'. "
                f"Known types: {sorted(_FIGURE_DISPATCH)}"
            )

        sel = workspace.load_selection(recipe.selection_slug)
        tracks_df = client.select(sel.run_id, sel.criteria)

        slug = f"{recipe.selection_slug}_{recipe.figure_type}_{uuid.uuid4().hex[:6]}"
        out_path = workspace.root / "figures" / f"{slug}.png"
        out_path.parent.mkdir(parents=True, exist_ok=True)

        kind = _FIGURE_DISPATCH[recipe.figure_type]
        variable = recipe.variables[0] if recipe.variables else "max_reflectivity_dbz"

        if kind == "histogram":
            from adapt.consumers.console.plots.population import render_histogram

            render_histogram(tracks_df, variable, out_path, style=recipe.style)

        elif kind == "scatter":
            from adapt.consumers.analysis.population import joint_distribution
            from adapt.consumers.console.plots.population import render_scatter

            x_var = recipe.variables[0] if len(recipe.variables) > 0 else "max_area_km2"
            y_var = recipe.variables[1] if len(recipe.variables) > 1 else "max_reflectivity_dbz"
            joint = joint_distribution(tracks_df, x_var, y_var)
            render_scatter(joint, out_path, style=recipe.style)

        elif kind == "composite":
            from adapt.consumers.analysis.lifecycle import compute_composite, normalize_time
            from adapt.consumers.console.plots.lifecycle import render_composite

            histories = [
                client.track_history(sel.run_id, uid) for uid in tracks_df["cell_uid"].tolist()
            ]
            import pandas as pd

            combined = pd.concat(histories, ignore_index=True) if histories else tracks_df
            normed = normalize_time(combined, variable)
            composite = compute_composite(normed, variable)
            render_composite(composite, out_path, style=recipe.style)

        elif kind == "heatmap":
            from adapt.consumers.analysis.lifecycle import compute_density, normalize_time
            from adapt.consumers.console.plots.lifecycle import render_heatmap

            histories = [
                client.track_history(sel.run_id, uid) for uid in tracks_df["cell_uid"].tolist()
            ]
            import pandas as pd

            combined = pd.concat(histories, ignore_index=True) if histories else tracks_df
            normed = normalize_time(combined, variable)
            density = compute_density(normed, variable)
            render_heatmap(density, variable, out_path, style=recipe.style)

        workspace._db.save_figure(
            slug=slug,
            display_name=f"{recipe.figure_type} — {recipe.selection_slug}",
            selection_slug=recipe.selection_slug,
            figure_type=recipe.figure_type,
            recipe_json=json.dumps(recipe.to_dict()),
            style=recipe.style,
            file_path=str(out_path),
        )

        return out_path
