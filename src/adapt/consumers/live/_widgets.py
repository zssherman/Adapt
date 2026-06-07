# Copyright © 2026, UChicago Argonne, LLC
# See LICENSE for terms and disclaimer.

"""Custom Tkinter and matplotlib widgets for the dashboard — no business logic."""

import contextlib
import logging
import re
import tkinter as tk

logger = logging.getLogger(__name__)

try:
    from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk

    _HAS_MPL = True
except ImportError:
    _HAS_MPL = False

try:
    from pyproj import Transformer

    _HAS_PROJ = True
except ImportError:
    _HAS_PROJ = False


# ── Compact navigation toolbar ────────────────────────────────────────────────

_CompactToolbar: type | None = None
if _HAS_MPL:

    class _CompactToolbarCls(NavigationToolbar2Tk):
        toolitems: tuple = tuple(
            t for t in NavigationToolbar2Tk.toolitems if t[0] not in ("Back", "Forward")
        )

        def __init__(self, canvas, window, *, pack_toolbar=True, lat0=0.0, lon0=0.0):
            self._ltrans = None
            if _HAS_PROJ and (lat0 or lon0):
                with contextlib.suppress(Exception):
                    self._ltrans = Transformer.from_crs(
                        f"+proj=aeqd +lat_0={lat0} +lon_0={lon0} +units=m",
                        "EPSG:4326",
                        always_xy=True,
                    )
            super().__init__(canvas, window, pack_toolbar=pack_toolbar)

        def set_message(self, s):
            if self._ltrans is not None and s and "x=" in s:
                try:
                    toks = {
                        t.split("=")[0]: float(t.split("=")[1])
                        for t in s.split()
                        if "=" in t and len(t.split("=")) == 2
                    }
                    x_km = toks.get("x", 0.0)
                    y_km = toks.get("y", 0.0)
                    lon_v, lat_v = self._ltrans.transform(x_km * 1000.0, y_km * 1000.0)
                    s = f"x={x_km:.2f}  y={y_km:.2f}    {lat_v:.4f}°  {lon_v:.4f}°"
                except Exception:
                    logger.exception("Failed to update toolbar coordinate message")
            super().set_message(s)

        def save_figure(self, *args):
            """Open save dialog with a filename derived from the radar-axis title."""
            from tkinter import filedialog

            title = self._title_from_figure()
            initialfile = title + ".png" if title else "adapt_scan.png"
            filetypes = [
                ("PNG image", "*.png"),
                ("PDF document", "*.pdf"),
                ("SVG image", "*.svg"),
                ("All files", "*"),
            ]
            path = filedialog.asksaveasfilename(
                parent=self.canvas.get_tk_widget(),
                title="Save figure",
                initialfile=initialfile,
                defaultextension=".png",
                filetypes=filetypes,
            )
            if path:
                self.canvas.figure.savefig(path, dpi=150, bbox_inches="tight")

        def _title_from_figure(self) -> str:
            """Extract the radar-axis title and convert it to a safe filename stem."""
            try:
                ax = self.canvas.figure.axes[0]
                raw = ax.get_title()
            except (IndexError, AttributeError):
                return ""
            # "KOUN  Reflectivity [2026-06-04 14:23:00 UTC]"
            # → "KOUN_Reflectivity_2026-06-04_14-23-00_UTC"
            safe = re.sub(r"[\[\]]", "", raw)  # remove brackets
            safe = re.sub(r"\s+", "_", safe.strip())  # spaces → underscores
            safe = re.sub(r"[:/\\|?*\"<>]", "-", safe)  # illegal path chars → dash
            safe = re.sub(r"_+", "_", safe)  # collapse multiple underscores
            return safe.strip("_")

    _CompactToolbar = _CompactToolbarCls


# ── Range slider widget ───────────────────────────────────────────────────────


class _RangeSlider(tk.Canvas):
    """Single-bar dual-handle range slider."""

    _PAD = 10
    _R = 7
    _CY = 14

    def __init__(self, parent, from_, to, lo_var, hi_var, fmt=".1f", **kw):
        kw.setdefault("height", 28)
        kw.setdefault("highlightthickness", 0)
        super().__init__(parent, **kw)
        self._from, self._to = from_, to
        self._lo, self._hi = lo_var, hi_var
        self._fmt = fmt
        self._drag = None
        self.bind("<Configure>", lambda _: self._draw())
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", lambda _: setattr(self, "_drag", None))
        lo_var.trace_add("write", lambda *_: self._draw())
        hi_var.trace_add("write", lambda *_: self._draw())

    def _tw(self):
        return max(self.winfo_width(), 160) - 2 * self._PAD

    def _v2x(self, v):
        ratio = (v - self._from) / (self._to - self._from)
        return self._PAD + max(0.0, min(1.0, ratio)) * self._tw()

    def _x2v(self, x):
        ratio = (x - self._PAD) / self._tw()
        return self._from + max(0.0, min(1.0, ratio)) * (self._to - self._from)

    def _draw(self):
        self.delete("all")
        w = self._PAD + self._tw() + self._PAD
        cy = self._CY
        lx = self._v2x(self._lo.get())
        hx = self._v2x(self._hi.get())
        r = self._R
        self.create_line(
            self._PAD, cy, w - self._PAD, cy, fill="#cccccc", width=4, capstyle="round"
        )
        self.create_line(lx, cy, hx, cy, fill="#4a9eca", width=4, capstyle="round")
        for x, tag in ((lx, "lo"), (hx, "hi")):
            self.create_oval(
                x - r,
                cy - r,
                x + r,
                cy + r,
                fill="#2980b9",
                outline="#1a5276",
                width=1,
                tags=tag,
            )

    def _on_press(self, event):
        lx = self._v2x(self._lo.get())
        hx = self._v2x(self._hi.get())
        self._drag = "lo" if abs(event.x - lx) <= abs(event.x - hx) else "hi"

    def _on_drag(self, event):
        val = self._x2v(event.x)
        if self._drag == "lo":
            self._lo.set(min(val, self._hi.get()))
        else:
            self._hi.set(max(val, self._lo.get()))
        self.event_generate("<<RangeChanged>>")
