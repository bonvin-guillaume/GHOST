#!/usr/bin/env python3
"""Plot signal and background spectra from two MISS plot selections.

Each selection is either a single scan-angle click or a dragged y-range
(average over those rows). Called by miss_spectrum_server.py:

    python plot_miss_click_spectrum.py \\
        --filename MISS-20200101-213100.pgm \\
        --signal-json '{"kind":"point","x":400,"y":120}' \\
        --bg-json '{"kind":"range","y0":150,"y1":180}' \\
        --natural-width 928 --natural-height 567
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
PLOTS_DIR = ROOT / "MISS_plots"
GHOST_CSV = ROOT / "ghost_df.csv"


def build_file_index(csv_path: Path = GHOST_CSV) -> dict[str, Path]:
    """Map MISS filename → absolute path using ghost_df.csv."""
    df = pd.read_csv(csv_path)
    index: dict[str, Path] = {}
    for _, row in df.iterrows():
        if row.get("miss_files_found", 0) <= 0:
            continue
        folder = Path(str(row["miss_folder_path"]))
        files = row["miss_files_list"]
        if isinstance(files, str):
            try:
                files = ast.literal_eval(files)
            except (ValueError, SyntaxError):
                files = []
        if not isinstance(files, list):
            continue
        for name in files:
            index[str(name)] = folder / str(name)
    return index


def plot_png_stem(filename: str) -> str:
    if filename.endswith(".pgm"):
        return filename.replace(".pgm", "_plot")
    if filename.endswith(".png") and not filename.endswith("_plot.png"):
        return filename.replace(".png", "_plot")
    if filename.endswith("_plot.png"):
        return filename[: -len(".png")]
    return filename + "_plot"


def load_sidecar(filename: str, natural_width: int | None, natural_height: int | None) -> dict:
    stem = plot_png_stem(filename)
    sidecar_path = PLOTS_DIR / f"{stem}.json"
    if sidecar_path.is_file():
        with open(sidecar_path, encoding="utf-8") as f:
            meta = json.load(f)
        print(f"[spectrum] Loaded axes metadata: {sidecar_path}")
        return meta

    print(
        f"[spectrum] WARNING: missing {sidecar_path}; "
        "using full-image fallback (re-run plot_MISS1/2 for accuracy)",
        file=sys.stderr,
    )
    if filename.startswith("MISS2-"):
        instrument = "MISS2"
        wl_max = 690
        y_top, y_bottom = 200, 0
    else:
        instrument = "MISS1"
        wl_max = 700
        y_top, y_bottom = 0, 200

    w = float(natural_width or 1000)
    h = float(natural_height or 600)
    return {
        "instrument": instrument,
        "wavelength_min": 400,
        "wavelength_max": wl_max,
        "scan_min": 0,
        "scan_max": 200,
        "y_top_is_scan": y_top,
        "y_bottom_is_scan": y_bottom,
        "n_scan": 200,
        "image_size_px": [w, h],
        "axes_bbox_px": [0.0, 0.0, w, h],
    }


def pixel_to_data(x: float, y: float, meta: dict, natural_width: int, natural_height: int):
    """Map PNG pixel (origin top-left) → (wavelength_nm, scan_label, row).

    Array row is always indexed from the *top* of the axes (row 0), matching
    imshow(origin='upper'). Scan-axis tick values (y_top_is_scan /
    y_bottom_is_scan) may be flipped between MISS1 and MISS2 and are only used
    as a display label — not as the row index.
    """
    left, bottom, width, height = meta["axes_bbox_px"]
    img_w, img_h = meta.get("image_size_px", [natural_width, natural_height])

    scale_x = float(img_w) / float(natural_width) if natural_width else 1.0
    scale_y = float(img_h) / float(natural_height) if natural_height else 1.0
    x_img = x * scale_x
    y_img = y * scale_y

    y_from_bottom = float(img_h) - y_img
    x_frac = (x_img - left) / width if width else 0.0
    y_frac_from_bottom = (y_from_bottom - bottom) / height if height else 0.0
    x_frac = float(np.clip(x_frac, 0.0, 1.0))
    y_frac_from_bottom = float(np.clip(y_frac_from_bottom, 0.0, 1.0))
    y_frac_from_top = 1.0 - y_frac_from_bottom

    wl_min = float(meta["wavelength_min"])
    wl_max = float(meta["wavelength_max"])
    wavelength = wl_min + x_frac * (wl_max - wl_min)

    scan_top = float(meta["y_top_is_scan"])
    scan_bottom = float(meta["y_bottom_is_scan"])
    scan = scan_top + y_frac_from_top * (scan_bottom - scan_top)

    n_scan = int(meta.get("n_scan", 200))
    # Row index follows image top → bottom, not the possibly-flipped scan labels.
    row = int(np.clip(round(y_frac_from_top * (n_scan - 1)), 0, n_scan - 1))
    return wavelength, scan, row


def load_spectral(filename: str, file_path: Path):
    if filename.startswith("MISS2-") or filename.endswith(".png"):
        from plot_MISS2 import miss2spectral

        spectral, wavelengths = miss2spectral(str(file_path))
        return spectral, np.asarray(wavelengths)
    from plot_MISS1 import read_miss_spectral

    spectral = read_miss_spectral(str(file_path))
    wavelengths = np.arange(400, 400 + spectral.shape[1])
    return spectral, wavelengths


def extract_spectrum(
    spectral: np.ndarray,
    selection: dict,
    meta: dict,
    natural_width: int,
    natural_height: int,
    role: str,
):
    """Return (spectrum_1d, label, info_dict) for a point or y-range selection."""
    kind = selection.get("kind", "point")

    if kind == "range":
        y0 = float(selection["y0"])
        y1 = float(selection["y1"])
        if "x0" in selection and "x1" in selection:
            x_mid = 0.5 * (float(selection["x0"]) + float(selection["x1"]))
        else:
            x_mid = float(selection.get("x", 0))
        _, scan0, row0 = pixel_to_data(x_mid, y0, meta, natural_width, natural_height)
        _, scan1, row1 = pixel_to_data(x_mid, y1, meta, natural_width, natural_height)
        r0, r1 = sorted((row0, row1))
        spec = np.mean(spectral[r0 : r1 + 1, :], axis=0)
        label = f"{role.capitalize()} (mean rows {r0}–{r1})"
        info = {
            "kind": "range",
            "row0": r0,
            "row1": r1,
            "scan0": min(scan0, scan1),
            "scan1": max(scan0, scan1),
        }
        print(
            f"[spectrum] {role} range y=({y0:.0f},{y1:.0f}) "
            f"→ rows {r0}–{r1} (scan≈{info['scan0']:.1f}–{info['scan1']:.1f})"
        )
        return spec, label, info

    x = float(selection["x"])
    y = float(selection["y"])
    wl, scan, row = pixel_to_data(x, y, meta, natural_width, natural_height)
    spec = spectral[row, :]
    label = f"{role.capitalize()} (row {row}, λ≈{wl:.0f} nm)"
    info = {"kind": "point", "row": row, "scan": scan, "wavelength": wl}
    print(
        f"[spectrum] {role} point ({x:.0f},{y:.0f}) "
        f"→ row={row}, scan≈{scan:.1f}, λ≈{wl:.1f}"
    )
    return spec, label, info


def _row_span(info: dict) -> tuple[int, int]:
    """Return inclusive (row0, row1) for a point or range selection."""
    if info.get("kind") == "range":
        return int(info["row0"]), int(info["row1"])
    row = int(info["row"])
    return row, row


def _row_to_display_y(row: float, n_rows: int, y_top: float, y_bottom: float) -> float:
    """Map spectral-array row index to imshow y (with origin='upper' + extent)."""
    return y_top + (row / n_rows) * (y_bottom - y_top)


def _mark_rows(
    ax,
    row0: int,
    row1: int,
    n_rows: int,
    y_top: float,
    y_bottom: float,
    color: str,
    label: str,
):
    """Highlight a scan-row span on the spectral-image axes."""
    y_a = _row_to_display_y(row0, n_rows, y_top, y_bottom)
    y_b = _row_to_display_y(row1 + 1, n_rows, y_top, y_bottom)
    ax.axhspan(y_a, y_b, color=color, alpha=0.35, label=label, zorder=3)
    if row0 == row1:
        y_mid = _row_to_display_y(row0 + 0.5, n_rows, y_top, y_bottom)
        ax.axhline(y_mid, color=color, linewidth=1.6, alpha=0.95, zorder=4)


def plot_spectra(
    filename: str,
    wavelengths: np.ndarray,
    spectral: np.ndarray,
    signal_spec: np.ndarray,
    bg_spec: np.ndarray,
    signal_label: str,
    bg_label: str,
    signal_info: dict,
    bg_info: dict,
    meta: dict,
):
    wl_min = float(meta.get("wavelength_min", wavelengths[0]))
    wl_max = float(meta.get("wavelength_max", wavelengths[-1]))
    y_top = float(meta.get("y_top_is_scan", 0))
    y_bottom = float(meta.get("y_bottom_is_scan", spectral.shape[0]))
    n_rows = int(spectral.shape[0])

    fig, (ax_spec, ax_img) = plt.subplots(
        2,
        1,
        figsize=(10, 9),
        gridspec_kw={"height_ratios": [1.2, 1.0]},
    )

    ax_spec.plot(wavelengths, signal_spec, label=signal_label, linewidth=1.8, color="#1f77b4")
    ax_spec.plot(wavelengths, bg_spec, label=bg_label, linewidth=1.8, color="#ff7f0e")
    ax_spec.set_xlabel("Wavelength [nm]")
    ax_spec.set_ylabel("Counts")
    ax_spec.set_title(filename)
    ax_spec.legend()
    ax_spec.grid(True, alpha=0.3)

    ax_img.imshow(
        np.sqrt(np.maximum(spectral, 0)),
        aspect="auto",
        extent=[wl_min, wl_max, y_bottom, y_top],
    )

    sig_r0, sig_r1 = _row_span(signal_info)
    bg_r0, bg_r1 = _row_span(bg_info)
    _mark_rows(ax_img, sig_r0, sig_r1, n_rows, y_top, y_bottom, "#1f77b4", "Signal rows")
    _mark_rows(ax_img, bg_r0, bg_r1, n_rows, y_top, y_bottom, "#ff7f0e", "Background rows")

    ax_img.set_xlabel("Wavelength [nm]")
    # Match y-axis ticks/label used in plot_MISS1.py / plot_MISS2.py
    tick_labels = ["South", "-60", "-30", "Zenith", "30", "60", "North"]
    if str(meta.get("instrument", "")).upper() == "MISS2":
        ax_img.set_yticks(np.linspace(0, 200, num=7))
    else:
        ax_img.set_yticks(np.linspace(200, 0, num=7))
    ax_img.set_yticklabels(tick_labels)
    ax_img.set_ylabel("Angle from zenith [deg]")
    ax_img.grid(axis="both", linestyle="--", linewidth=0.5, alpha=0.7)
    ax_img.set_title(
        f"Selected rows — signal {sig_r0}"
        + (f"–{sig_r1}" if sig_r1 != sig_r0 else "")
        + f", background {bg_r0}"
        + (f"–{bg_r1}" if bg_r1 != bg_r0 else "")
    )
    ax_img.legend(loc="upper right", fontsize=8)

    fig.tight_layout()
    print(
        f"[spectrum] Showing plot for {filename} "
        f"(signal rows {sig_r0}–{sig_r1}, background rows {bg_r0}–{bg_r1})"
    )
    plt.show()


def _parse_selection(raw: str) -> dict:
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("selection JSON must be an object")
    kind = data.get("kind", "point")
    if kind == "point":
        if "x" not in data or "y" not in data:
            raise ValueError("point selection needs x and y")
    elif kind == "range":
        if "y0" not in data or "y1" not in data:
            raise ValueError("range selection needs y0 and y1")
    else:
        raise ValueError(f"unknown selection kind: {kind}")
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--filename", required=True, help="MISS source filename")
    parser.add_argument("--signal-json", required=True, help="Signal selection JSON")
    parser.add_argument("--bg-json", required=True, help="Background selection JSON")
    parser.add_argument("--natural-width", type=int, default=0)
    parser.add_argument("--natural-height", type=int, default=0)
    args = parser.parse_args(argv)

    filename = args.filename
    if filename.endswith("_plot.png"):
        if filename.startswith("MISS2-"):
            filename = filename.replace("_plot.png", ".png")
        else:
            filename = filename.replace("_plot.png", ".pgm")

    try:
        signal_sel = _parse_selection(args.signal_json)
        bg_sel = _parse_selection(args.bg_json)
    except (json.JSONDecodeError, ValueError) as exc:
        print(f"[spectrum] ERROR: bad selection JSON: {exc}", file=sys.stderr)
        return 1

    index = build_file_index()
    if filename not in index:
        print(f"[spectrum] ERROR: {filename} not found in {GHOST_CSV}", file=sys.stderr)
        return 1
    file_path = index[filename]
    if not file_path.is_file():
        print(f"[spectrum] ERROR: data file missing: {file_path}", file=sys.stderr)
        return 1

    natural_width = args.natural_width or 0
    natural_height = args.natural_height or 0
    meta = load_sidecar(filename, natural_width or None, natural_height or None)
    if not natural_width or not natural_height:
        natural_width = int(round(meta["image_size_px"][0]))
        natural_height = int(round(meta["image_size_px"][1]))

    print(f"[spectrum] Loading {file_path} …")
    spectral, wavelengths = load_spectral(filename, file_path)

    signal_spec, signal_label, signal_info = extract_spectrum(
        spectral, signal_sel, meta, natural_width, natural_height, "signal"
    )
    bg_spec, bg_label, bg_info = extract_spectrum(
        spectral, bg_sel, meta, natural_width, natural_height, "background"
    )

    plot_spectra(
        filename,
        wavelengths,
        spectral,
        signal_spec,
        bg_spec,
        signal_label,
        bg_label,
        signal_info,
        bg_info,
        meta,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
