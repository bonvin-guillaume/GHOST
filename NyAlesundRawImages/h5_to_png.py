"""
Batch-convert Ny Ålesund HDF5 raw images to 8-bit PNGs.

Each .h5 file contains datasets image01–image05 (2000×2000 uint16).
Writes one PNG per dataset as {IDnetwork}_{DateNN}.png using HDF5 root attributes.

@author: Guillaume Bonvin
"""

from pathlib import Path

import h5py
import numpy as np
from PIL import Image


def _attr_str(attrs, name):
    """Read an HDF5 attribute as a plain string."""
    val = attrs[name]
    if isinstance(val, bytes):
        return val.decode()
    if hasattr(val, "item"):
        return str(val.item())
    return str(val)


def png_name_for_dataset(attrs, dataset_key):
    """Build output filename stem: IDnetwork + DateNN for imageNN."""
    suffix = dataset_key.removeprefix("image")
    date_key = f"Date{suffix}"
    network_id = _attr_str(attrs, "IDnetwork")
    date_stamp = _attr_str(attrs, date_key)
    return f"{network_id}_{date_stamp}"


def uint16_to_uint8(img, p_low=1, p_high=99):
    """Scale uint16 image to uint8 using percentile stretch."""
    lo, hi = np.percentile(img, [p_low, p_high])
    if hi == lo:
        lo, hi = float(img.min()), float(img.max())
    if hi == lo:
        return np.zeros(img.shape, dtype=np.uint8)
    scaled = (img.astype(np.float64) - lo) / (hi - lo) * 255.0
    return np.clip(scaled, 0, 255).astype(np.uint8)


def convert_file(h5_path):
    """Convert all datasets in one HDF5 file to PNGs. Returns number written."""
    written = 0
    out_dir = h5_path.parent

    with h5py.File(h5_path, "r") as f:
        for key in sorted(f.keys()):
            out_path = out_dir / f"{png_name_for_dataset(f.attrs, key)}.png"
            img = f[key][:]
            png_data = uint16_to_uint8(img)
            Image.fromarray(png_data, mode="L").save(out_path)
            print(f"  wrote {out_path.name}")
            written += 1

    return written


def main():
    data_dir = Path(__file__).resolve().parent
    h5_files = sorted(data_dir.glob("*.h5"))
    if not h5_files:
        print(f"No .h5 files found in {data_dir}")
        return

    total_written = 0
    for h5_path in h5_files:
        print(h5_path.name)
        total_written += convert_file(h5_path)

    print(f"\nDone: {len(h5_files)} HDF5 file(s), {total_written} PNG(s) written")


if __name__ == "__main__":
    main()
