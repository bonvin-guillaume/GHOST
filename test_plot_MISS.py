"""
Plot a single MISS-1 (.pgm) or MISS-2 (.png) spectral file.

Edit MISS_FILE below (basename only), then run:
    python test_plot_MISS.py

@author: Guillaume Bonvin
"""

import os
import re

from process_events import MISS1_BASE_DIR, MISS2_BASE_DIR
from plot_MISS1 import read_miss_spectral
from plot_MISS1 import save_spectral_plot as save_miss1_plot
from plot_MISS2 import miss2spectral
from plot_MISS2 import save_spectral_plot as save_miss2_plot

# Basename of the MISS file to plot (path is resolved from the date in the name)
MISS_FILE = 'MISS-20211223-000900.pgm'
# MISS_FILE = 'MISS2-20241205-084945.png'

PLOTS_DIR = 'MISS_test_plots'

_FILENAME_RE = re.compile(
    r'^(MISS2?)-(\d{8})-(\d{6})(?:\.(pgm|png))?$',
    re.IGNORECASE,
)


def detect_instrument(filename):
    """Return '1' or '2' from filename / extension."""
    name = os.path.basename(filename)
    if name.startswith('MISS2-') or name.lower().endswith('.png'):
        return '2'
    if name.startswith('MISS-') or name.lower().endswith('.pgm'):
        return '1'
    raise ValueError(
        f'Cannot tell MISS-1 vs MISS-2 from {name!r}. '
        'Use a MISS-YYYYMMDD-HHMMSS.pgm or MISS2-YYYYMMDD-HHMMSS.png name.'
    )


def resolve_miss_path(filename):
    """Build the KHO path from the date encoded in a MISS basename."""
    name = os.path.basename(filename)
    match = _FILENAME_RE.match(name)
    if not match:
        raise ValueError(
            f'Expected MISS-YYYYMMDD-HHMMSS.pgm or MISS2-YYYYMMDD-HHMMSS.png, '
            f'got {name!r}'
        )

    prefix, ymd, _hms, ext = match.groups()
    year, month, day = ymd[:4], ymd[4:6], ymd[6:8]
    instrument = '2' if prefix.upper() == 'MISS2' else '1'
    if ext is None:
        name = name + ('.png' if instrument == '2' else '.pgm')

    base_dir = MISS2_BASE_DIR if instrument == '2' else MISS1_BASE_DIR
    return os.path.join(base_dir, year, month, day, name)


def plot_output_path(src_path):
    filename = os.path.basename(src_path)
    if filename.endswith('.pgm'):
        plot_filename = filename.replace('.pgm', '_plot.png')
    elif filename.endswith('.png'):
        plot_filename = filename.replace('.png', '_plot.png')
    else:
        plot_filename = filename + '_plot.png'
    return os.path.join(PLOTS_DIR, plot_filename)


def plot_miss_file(filename):
    src_path = resolve_miss_path(filename)
    if not os.path.isfile(src_path):
        raise FileNotFoundError(f'File not found: {src_path}')

    os.makedirs(PLOTS_DIR, exist_ok=True)
    instrument = detect_instrument(src_path)
    output_path = plot_output_path(src_path)
    basename = os.path.basename(src_path)

    print(f'MISS-{instrument}: {src_path}')
    print(f'  -> {output_path}')

    if instrument == '1':
        spectral = read_miss_spectral(src_path)
        save_miss1_plot(spectral, output_path, filename=basename)
    else:
        spectral, wavelengths = miss2spectral(src_path)
        save_miss2_plot(spectral, wavelengths, output_path, basename)

    print('Done.')
    return output_path


if __name__ == '__main__':
    plot_miss_file(MISS_FILE)

