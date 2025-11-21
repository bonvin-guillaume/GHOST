"""
Python script to read and plot spectral image files from MISS-1.

This script reads a MISS-1 .pgm file, corrects the "smiley" spectral image 
into a rectangular image, and creates visualizations of the spectral data.

Usage:
    python plot_MISS-1.py <path_to_pgm_file>

Created based on MISS-1 continuum detection.ipynb
"""

import os
import sys
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import medfilt2d


def readpgm(name):
    """
    Read ASCII PGM-file (P2 format).
    
    A user called Felix wrote a nice short reading routine for ASCII PGM-files
    https://stackoverflow.com/questions/46944048/how-to-read-pgm-p2-image-in-python
    
    The commonly used PIL for image reading in python seems to have trouble
    handling the comments in PGM-files, even though the comments are part
    of the "standard" for PNM-format.
    """
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
    """
    Reads a MISS-image and corrects the "smiley" spectral image into
    a nice rectangular image.

    Outputs a matrix with the vertical axis being a proxy for the scan
    angle (no calibration yet). The horizontal axis is wavelength from
    400nm to 700nm

    For each scan angle (image row), the known emission lines are used
    to first construct a mapping between wavelengths and pixel columns.
    Then the intensities for wavelengths between 400..700nm at 1nm steps
    are interpolated from the image.

    NOTE:
        - the wavelength calibration is based on only three points, or
          the blue, green and red emission lines
        - the "scan angle" is not calibrated at all!
    """
    im = readpgm(filename)

    # Use 2D meridian filtering to filter out noise
    im = medfilt2d(im)

    # Estimate the background level from an image corner and
    # remove the pixel offset
    bg_estimate = np.mean(im[0:29, 0:29])
    im = np.maximum(im - bg_estimate, 0).transpose()

    # From quick calibration using auroral emission lines,
    # see plot_misspeaks.m in the Matlab source code
    bluepoly = np.poly1d([-0.000401186790506, 0.118021155830754,
                          86.670020639834831])
    redpoly = np.poly1d([-0.0003147574819, 0.1045665634675,
                         656.6050051599582])
    greenpoly = np.poly1d([-0.0003805469556, 0.1139447884417,
                           462.5405056759545])

    # Create a spectral image
    # - use data between rows 70 and 270 (needs scan angle calibration!)
    # - interpolate data from 400..700nm

    scanangle = np.arange(0, 200)
    wavelengths = np.arange(400, 701)
    spectralimage = np.zeros([len(scanangle), len(wavelengths)])
    colIndex = np.arange(0, im.shape[1])

    print('This is the shape of the raw image: ', im.shape)

    for alpha in scanangle:
        row = 70 + alpha
        blueline = bluepoly(row)      # Locations of the auroral emission lines
        redline = redpoly(row)        # at this scan angle, or image row in raw
        greenline = greenpoly(row)    # image data
        lambdas = np.polynomial.Polynomial.fit([427.8, 557.7, 630.0],
                                               [blueline, greenline, redline], 2)
        cols = lambdas(wavelengths)
        thisrowvalues = im[row, :]
        spectralvalues = np.interp(cols, colIndex, thisrowvalues)
        spectralimage[alpha, :] = spectralvalues

    return spectralimage


def plot_spectral_image(spectralimage, selected_row=125):
    """
    Create plots of the spectral image.
    
    Creates two plots:
    1. 2D image of the spectral data with selected row highlighted
    2. Line plots of selected row and mean spectrum
    """
    # Plot 1: 2D spectral image
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.imshow(np.sqrt(spectralimage), aspect='auto',
              extent=[400, 700, 200, 0])
    ax.axhline(y=selected_row, color='red', linestyle='--', 
               linewidth=2, label=f'Row {selected_row}')
    ax.set_xlabel('Wavelength [nm]')
    ax.set_ylabel('Uncalibrated angle')
    ax.legend()
    ax.set_title('MISS-1 Spectral Image')
    plt.tight_layout()

    # Plot 2: Line plots of spectra
    fig, ax = plt.subplots(figsize=(10, 6))
    wavelengths_plot = np.linspace(400, 700, spectralimage.shape[1])
    ax.plot(wavelengths_plot, spectralimage[selected_row, :], 
            label=f'Row {selected_row}')
    ax.plot(wavelengths_plot, np.mean(spectralimage, axis=0), 
            label='Averaged over all angles', linewidth=2)
    ax.set_xlabel('Wavelength [nm]')
    ax.set_ylabel('Counts')
    ax.legend()
    ax.set_title('Spectral Line Plots')
    ax.grid(True, alpha=0.3)
    plt.tight_layout()


def plot_masked_spectrum(spectralimage, selected_row=125):
    """
    Plot spectrum with masked regions around emission lines.
    
    Masks out regions around the three auroral emission lines 
    (427.8, 557.7, 630.0 nm) to show continuum emission.
    """
    emission_lines = [427.8, 557.7, 630.0]
    mask_width = 10  # +/- 10 nm

    # Create wavelength array
    wavelengths = np.linspace(400, 700, spectralimage.shape[1])

    # Create mask for regions to exclude
    mask = np.ones(len(wavelengths), dtype=bool)
    for line in emission_lines:
        mask = mask & ((wavelengths < line - mask_width) | 
                       (wavelengths > line + mask_width))

    # Create masked spectrum (set masked regions to NaN for plotting)
    selected_spectrum = spectralimage[selected_row, :].copy()
    print(f"Mean of selected spectrum before masking: {np.mean(selected_spectrum):.2f}")
    selected_spectrum[~mask] = np.nan
    print(f"Mean of selected spectrum after masking: {np.nanmean(selected_spectrum):.2f}")

    mean_spectrum = np.mean(spectralimage, axis=0)
    print(f"Mean of averaged spectrum before masking: {np.mean(mean_spectrum):.2f}")
    mean_spectrum[~mask] = np.nan
    print(f"Mean of averaged spectrum after masking: {np.nanmean(mean_spectrum):.2f}")

    # Plot
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(wavelengths, selected_spectrum, 
            label=f'Row {selected_row} (masked)', linewidth=2, color='blue')
    ax.plot(wavelengths, mean_spectrum, 
            label='Mean spectrum (masked)', linewidth=2, color='green')
    ax.set_xlabel('Wavelength [nm]')
    ax.set_ylabel('Counts')
    ax.set_title('Spectrum with Masked Regions Around Emission Lines')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Add vertical lines to indicate masked regions
    for i, line in enumerate(emission_lines):
        label = 'Masked region' if i == 0 else ''
        ax.axvspan(line - mask_width, line + mask_width, 
                   alpha=0.2, color='red', label=label)

    plt.tight_layout()


def main():
    """Main function to read and plot PGM file."""
    if len(sys.argv) < 2:
        print("Usage: python plot_pgm.py <path_to_pgm_file>")
        print("\nExample:")
        print("  python plot_pgm.py Example_files/MISS-20200103-084900.pgm")
        sys.exit(1)

    filename = sys.argv[1]

    # Check if file exists
    if not os.path.exists(filename):
        print(f"Error: File '{filename}' not found!")
        sys.exit(1)

    print(f"Reading file: {filename}")
    
    # Read and process the spectral image
    spectralimage = read_miss_spectral(filename)
    
    # Select which row to plot (default: 125)
    selected_row = 125
    
    # Create plots
    print(f"\nCreating plots with selected row: {selected_row}")
    plot_spectral_image(spectralimage, selected_row)
    # plot_masked_spectrum(spectralimage, selected_row)
    
    # Show all plots
    plt.show()
    print("\nDone!")


if __name__ == "__main__":
    main()

