"""
This script handles plotting for MISS-1 .pgm spectral files.
Reads ASCII PGM files and generates spectral plots.

@author: Guillaume Bonvin
"""

import os
import ast
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import rotate
from scipy.signal import medfilt2d

row_offset = 70
PLOT_DPI = 100
PLOT_PAD_INCHES = 0.1


def _use_agg_backend():
    """Force non-interactive backend for batch PNG export."""
    import matplotlib
    matplotlib.use('Agg', force=True)
    global plt
    import matplotlib.pyplot as _plt
    plt = _plt


def write_plot_sidecar(fig, ax, output_path, meta):
    """Write JSON next to the PNG with axes bbox in saved-image pixels.

    axes_bbox_px is [left, bottom, width, height] with bottom measured from
    the bottom of the saved PNG (matplotlib convention).
    """
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    tight = fig.get_tightbbox(renderer).padded(PLOT_PAD_INCHES)
    ax_inches = ax.get_window_extent(renderer).transformed(
        fig.dpi_scale_trans.inverted()
    )
    dpi = fig.dpi
    left = (ax_inches.x0 - tight.x0) * dpi
    bottom = (ax_inches.y0 - tight.y0) * dpi
    width = ax_inches.width * dpi
    height = ax_inches.height * dpi
    meta = dict(meta)
    meta['image_size_px'] = [tight.width * dpi, tight.height * dpi]
    meta['axes_bbox_px'] = [left, bottom, width, height]
    meta['dpi'] = dpi
    sidecar_path = os.path.splitext(output_path)[0] + '.json'
    with open(sidecar_path, 'w', encoding='utf-8') as f:
        json.dump(meta, f, indent=2)

def readpgm(name):
    """Read ASCII PGM-file (P2 format)."""
    with open(name) as f:
        lines = f.readlines()

    # Ignores commented lines
    for l in list(lines):
        if l[0] == '#':
            lines.remove(l)

    # Makes sure it is ASCII format (P2)
    assert lines[0].strip() == 'P2', 'File not an ASCII PGM-file'

    # Converts data to a list of integers
    data = []
    for line in lines[1:]:
        data.extend([int(c) for c in line.split()])

    data = (np.array(data[3:]), (data[1], data[0]), data[2])
    return np.reshape(data[0], data[1])


def read_miss_spectral(filename):
    """Reads a MISS-image and corrects the "smiley" spectral image into a nice rectangular image."""
    im = readpgm(filename)

    # Use 2D meridian filtering to filter out noise
    im = medfilt2d(im)
    im = rotate(im, 0.1, reshape=False, order=1)

    # Estimate the background level from an image corner and remove the pixel offset
    bg_estimate = np.mean(im[0:29, 0:29])
    im = np.maximum(im - bg_estimate, 0).transpose()

    # From quick calibration using auroral emission lines
    bluepoly = np.poly1d([-0.000401186790506, 0.118021155830754, 86.670020639834831])
    redpoly = np.poly1d([-0.0003147574819, 0.1045665634675, 656.6050051599582])
    greenpoly = np.poly1d([-0.0003805469556, 0.1139447884417, 462.5405056759545])

    # Create a spectral image
    scanangle = np.arange(0, 200)
    wavelengths = np.arange(400, 701)
    spectralimage = np.zeros([len(scanangle), len(wavelengths)])
    colIndex = np.arange(0, im.shape[1])

    for alpha in scanangle:
        row = row_offset + alpha
        blueline = bluepoly(row)
        redline = redpoly(row)
        greenline = greenpoly(row)
        lambdas = np.polynomial.Polynomial.fit([427.8, 557.7, 630.0],
                                               [blueline, greenline, redline], 2)
        cols = lambdas(wavelengths)
        thisrowvalues = im[row, :]
        spectralvalues = np.interp(cols, colIndex, thisrowvalues)
        spectralimage[alpha, :] = spectralvalues

    return spectralimage


def save_spectral_plot(spectralimage, output_path, filename, selected_row=125):
    """Create and save plot of the spectral image."""
    _use_agg_backend()
    fig, ax = plt.subplots(figsize=(10, 6))
    im = ax.imshow(np.sqrt(spectralimage), aspect='auto', extent=[400, 700, 200, 0]) # dynamic range compression, nonlinear intensity stretch
    # im = ax.imshow(np.log10(spectralimage + 1), aspect='auto', extent=[400, 700, 200, 0]) # Log stretch: compresses the dynamic range even more and is often useful when intensities span several orders of magnitude
    cbar = fig.colorbar(im, ax=ax, fraction=0.02, pad=0.01)
    cbar.set_label(r'$\sqrt{\mathrm{Counts}}$', fontsize=10)
    tick_positions = np.linspace(200,0, num=7)
    tick_labels = ["South", "-60", "-30", "Zenith", "30", "60", "North"]
    ax.set_yticks(tick_positions)
    ax.set_yticklabels(tick_labels)
    ax.grid(axis='both', linestyle='--', linewidth=0.5, alpha=0.7)
    ax.set_xlabel('Wavelength [nm]')
    ax.set_ylabel('Angle from zenith [deg]') # Simple linear approximation
    title = f'{filename}'
    ax.set_title(title)
    plt.tight_layout()
    fig.set_dpi(PLOT_DPI)
    write_plot_sidecar(
        fig,
        ax,
        output_path,
        {
            'instrument': 'MISS1',
            'source_filename': filename,
            'wavelength_min': 400,
            'wavelength_max': 700,
            'scan_min': 0,
            'scan_max': 200,
            'y_top_is_scan': 0,
            'y_bottom_is_scan': 200,
            'n_scan': int(spectralimage.shape[0]),
            'n_wavelength': int(spectralimage.shape[1]),
        },
    )
    plt.savefig(
        output_path,
        dpi=PLOT_DPI,
        bbox_inches='tight',
        pad_inches=PLOT_PAD_INCHES,
    )
    plt.close(fig)


def generate_miss_plots(df, plots_dir='miss_plots'):
    """
    Generate spectral plots for all MISS .pgm files found in the dataframe.
    
    Args:
        df: DataFrame containing file lists
        plots_dir: Directory to save plots
    """
    # Create output directory for plots
    if not os.path.exists(plots_dir):
        os.makedirs(plots_dir)
    
    # Collect all unique PGM files from the dataframe
    all_pgm_files = []
    for idx, row in df.iterrows():
        if row['miss_files_found'] > 0:
            folder_path = row['miss_folder_path']
            # Handle the file list (could be string representation of list)
            miss_files = row['miss_files_list']
            if isinstance(miss_files, str):
                try:
                    miss_files = ast.literal_eval(miss_files)
                except:
                    miss_files = []
            
            for filename in miss_files:
                if filename.endswith('.pgm'):
                    file_path = os.path.join(folder_path, filename)
                    all_pgm_files.append((file_path, filename))
    
    print(f"Found {len(all_pgm_files)} PGM files to process")
    
    # Generate plots for each PGM file
    successful_plots = 0
    failed_plots = []
    
    for i, (file_path, filename) in enumerate(all_pgm_files, 1):
        try:
            print(f"Processing {i}/{len(all_pgm_files)}: {filename}...", end=' ')
            
            # Read spectral image
            spectralimage = read_miss_spectral(file_path)
            
            # Save plot
            plot_filename = filename.replace('.pgm', '_plot.png')
            plot_path = os.path.join(plots_dir, plot_filename)
            save_spectral_plot(spectralimage, plot_path, filename=filename)
            
            successful_plots += 1
            print("✓")
        except Exception as e:
            print(f"✗ Error: {str(e)}")
            failed_plots.append((filename, str(e)))
    
    print(f"\nCompleted: {successful_plots}/{len(all_pgm_files)} plots generated successfully")
    if failed_plots:
        print(f"Failed: {len(failed_plots)} files")
        for fname, error in failed_plots[:5]:  # Show first 5 failures
            print(f"  - {fname}: {error}")
    
    return successful_plots, failed_plots


if __name__ == '__main__':
    # Example usage: load the dataframe and generate plots
    input_csv = 'ghost_df.csv'
    plots_dir = 'MISS_plots'
    
    print(f"Reading {input_csv}...")
    df = pd.read_csv(input_csv)
    print(f"DataFrame shape: {df.shape}")
    
    print("\nGenerating MISS-1 spectral plots...")
    generate_miss_plots(df, plots_dir)

