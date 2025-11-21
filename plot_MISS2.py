# -*- coding: utf-8 -*-
"""
Read a MISS2 image and remove the "smiley". The return image has
columns corresponding to wavelengths from 400 to 690nm with 1nm
steps. The rows correspond to uncalibrated zenith angle from north
(top of image) to south (bottom of image).

Mikko Syrjäsuo/UNIS, 2025-11-16

"""
from datetime import datetime
from os.path import isfile, join, basename
from glob import glob # It might be better to get an iterator?

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as colors
from mpl_toolkits.axes_grid1 import make_axes_locatable
from matplotlib import transforms
from scipy.signal import medfilt2d
from PIL import Image

def miss2spectral(missFile):
    """
    The estimated "smiley", see miss2_calibration.py
    Note that, in the first setup, the polynomials
    were estimated using only three auroral emission lines.
    The most serious issue is the lack of a reference in
    the blue end of the spectrum.
    TO DO: use data where the auroral blue emission line is
           also visible
    """
    p_blue=np.poly1d([-0.0004351, 0.1633, 68.56])
    p_green=np.poly1d([-0.0004285, 0.1651, 541.5])
    p_red=np.poly1d([-0.0002597, 0.09893, 799.2])
    p_red2=np.poly1d([-0.0002486, 0.09992, 820.4])


    """
    Based on the testplots, the wavelength range roughly 
    from 398nm to 697nm, so let's use 400 to 690nm as the 
    range to be interpolated from the spectral image. 
    In other words, the "scan angle" or zenith angle from north
    to south is roughly from row 70 to 270.
    """

    missImage=np.array(Image.open(missFile))
    imsize=np.shape(missImage)
    im=np.fliplr(np.rot90(missImage))

    # Use 2D meridian filtering to filter out noise
    im = medfilt2d(im)

    # Estimate the background level from an image corner and
    # remove the pixel offset
    bg_estimate=np.mean(im[0:29,0:29])
    im=np.maximum(im-bg_estimate,0)

    """
    Create a spectral image where each column represents a constant wavelength
    - use data between 70 to 270 rows for the zenith angle, which
      results in roughly one degree resolution along the meridian
    - interpolate new datapoints for a range 400-690nm
    """

    scanangle=np.arange(0,200) # 270-70=200
    wavelengths=np.arange(400,691)
    spectralImage=np.zeros([len(scanangle),len(wavelengths)])
    colIndex=np.arange(0,im.shape[1])

    for alpha in scanangle:
        row=70+alpha
        blueline=p_blue(row)
        greenline=p_green(row)
        redline=p_red(row)
        red2line=p_red2(row)

        waves=np.polynomial.Polynomial.fit([427.8, 557.7, 630.0, 636.4], 
                                           [blueline, greenline,redline,red2line],2)

        cols=waves(wavelengths) # Pixel columns corresponding to wavelengths
        thisrowvalues=im[row,:]
        spectralValues=np.interp(cols, colIndex, thisrowvalues)
        spectralImage[alpha,:]=spectralValues
    return spectralImage, wavelengths


def save_spectral_plot(spectralImage, wavelengths, output_path, filename):
    """Create and save plot of the spectral image."""
    fig, axMiss = plt.subplots(figsize=(10,6))
    fig.suptitle(filename)

    pos=axMiss.imshow(np.sqrt(spectralImage), aspect='auto',
                extent=[min(wavelengths),max(wavelengths),0, 200],
                vmin=0)
    axMiss.set_xlabel('Wavelength [nm]')
    axMiss.set_ylabel('Uncalibrated zenith angle')
    tick_positions = np.linspace(0,200, num=7)
    tick_labels = ["South", "-60", "-30", "Zenith", "30", "60", "North"]
    axMiss.set_yticks(tick_positions)
    axMiss.set_yticklabels(tick_labels)
    axMiss.grid(False)
    # fig.colorbar(pos, ax=axMiss, label="Counts")
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=100, bbox_inches='tight')
    plt.close(fig)


if __name__ == "__main__":
    import os
    import ast
    
   # Create output directory for plots
    plots_dir = 'MISS_plots'
    if not os.path.exists(plots_dir):
        os.makedirs(plots_dir)

    df = pd.read_csv('ghost_df.csv')

    all_png_files = []
    for idx, row in df.iterrows():
        if row['miss_files_found'] > 0:
            folder_path = row['miss_folder_path']
            # Parse the string representation of the list into an actual list
            files_list = ast.literal_eval(row['miss_files_list'])
            for filename in files_list:
                if filename.startswith('MISS2-'):
                    file_path = os.path.join(folder_path, filename)
                    all_png_files.append((file_path, filename))


    print(f"Found {len(all_png_files)} PNG files to process")
    
    # Generate plots for each PNG file
    successful_plots = 0
    failed_plots = []
    
    for i, (file_path, filename) in enumerate(all_png_files, 1):
        try:
            print(f"Processing {i}/{len(all_png_files)}: {filename}...", end=' ')
            
            # Process spectral image
            spectralImage, wavelengths = miss2spectral(file_path)
            
            # Save plot
            plot_filename = filename.replace('.png', '_plot.png')
            plot_path = join(plots_dir, plot_filename)
            save_spectral_plot(spectralImage, wavelengths, plot_path, filename)
            
            successful_plots += 1
            print("✓")
        except Exception as e:
            print(f"✗ Error: {str(e)}")
            failed_plots.append((filename, str(e)))
    
    print(f"\nCompleted: {successful_plots}/{len(all_png_files)} plots generated successfully")
    if failed_plots:
        print(f"Failed: {len(failed_plots)} files")
        for fname, error in failed_plots[:5]:  # Show first 5 failures
            print(f"  - {fname}: {error}")