"""
This script handles plotting for MISS-1 .pgm spectral files.
Reads ASCII PGM files and generates spectral plots.

@author: Guillaume Bonvin
"""

import os
import ast
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
from scipy.signal import medfilt2d

row_offset = 70

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
    ax.set_ylabel('Scan angle from zenith [deg]') # Simple linear approximation
    title = f'{filename}'
    ax.set_title(title)
    plt.tight_layout()
    plt.savefig(output_path, dpi=100, bbox_inches='tight')
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

