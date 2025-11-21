"""
This script generates an interactive HTML table from the processed ghost_df.csv file.
The HTML table includes clickable links to MISS, SONY, and GOA files with inline viewers.

Optional: Also generates spectral plots for MISS .pgm files.

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
        row = 70 + alpha
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
    ax.imshow(np.sqrt(spectralimage), aspect='auto', extent=[400, 700, 200, 0])
    ax.set_xlabel('Wavelength [nm]')
    ax.set_ylabel('Uncalibrated angle')
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


def create_file_links(folder_path, file_list, label):
    """Create HTML links for individual files in a scrollable container
    For MISS/MISS2 files, creates links to generated plot images
    For SONY and other files, creates direct file links
    """
    # Handle the case where file_list might be a string representation of a list
    if isinstance(file_list, str):
        try:
            file_list = ast.literal_eval(file_list)
        except:
            file_list = []
    
    if not file_list or len(file_list) == 0:
        return '-'
    
    # Create links for ALL files (no limit)
    links = []
    for filename in file_list:
        # Construct full file path
        file_path = folder_path + '\\' + filename
        
        # For MISS .pgm files, create links to the generated plot images
        if label == 'MISS' and filename.endswith('.pgm') and filename.startswith('MISS-'):
            # Link to the generated plot PNG (MISS-1)
            plot_filename = filename.replace('.pgm', '_plot.png')
            plot_path = os.path.join('miss_plots', plot_filename)
            
            # Convert to file:// URL for the plot image
            plot_url = 'file:///' + os.path.abspath(plot_path).replace('\\', '/')
            
            # Create link with filename that opens the plot
            links.append(f'<a href="{plot_url}" target="_blank" title="View spectral plot">{filename} 📊</a>')
        # For MISS2 files, create links to the generated plot images
        elif label == 'MISS' and filename.startswith('MISS2-'):
            # Link to the generated plot PNG (MISS-2)
            plot_filename = filename.replace('.png', '_plot.png')
            plot_path = os.path.join('miss_plots', plot_filename)
            
            # Convert to file:// URL for the plot image
            plot_url = 'file:///' + os.path.abspath(plot_path).replace('\\', '/')
            
            # Create link with filename that opens the plot
            links.append(f'<a href="{plot_url}" target="_blank" title="View spectral plot">{filename} 📈</a>')
        else:
            # For SONY and other files, create direct file links
            # Convert to file:// URL
            if file_path.startswith('\\\\'):
                # Network path: \\server\share -> file://server/share
                file_url = 'file:' + file_path.replace('\\', '/')
            else:
                # Local path
                file_url = 'file:///' + file_path.replace('\\', '/')
            
            # Create link with just the filename (shorter display)
            links.append(f'<a href="{file_url}" target="_blank">{filename}</a>')
    
    # Join all links with line breaks
    links_html = '<br>'.join(links)
    
    # Put in a scrollable div with fixed height
    # Show file count at the top
    # Width set to fit one filename (about 240px for typical filename length)
    # Max-height set to show ~5 files at a time (120px)
    return f'<div style="width: 240px; font-size: 0.9em;"><div style="font-weight: bold; margin-bottom: 5px; color: #a0a0a0;">{len(file_list)} file(s)</div><div style="max-height: 120px; overflow-y: auto; border: 1px solid rgba(255, 255, 255, 0.1); padding: 5px; white-space: nowrap; border-radius: 4px; background: rgba(0, 0, 0, 0.2);">{links_html}</div></div>'


def generate_html_table(input_csv='ghost_df.csv', output_html='ghost_events_table.html', 
                        generate_plots=True, plots_dir='miss_plots'):
    """
    Generate an interactive HTML table from the processed ghost_df.csv file.
    
    Args:
        input_csv: Path to input CSV file with processed GHOST events
        output_html: Path to output HTML file
        generate_plots: Whether to generate MISS plots (default: True)
        plots_dir: Directory to save/read MISS plots
    """
    # Read the processed CSV file
    print(f"Reading {input_csv}...")
    df = pd.read_csv(input_csv)
    
    print(f"DataFrame shape: {df.shape}")
    
    # Generate MISS plots if requested
    if generate_plots:
        print("\nGenerating MISS spectral plots...")
        generate_miss_plots(df, plots_dir)
    
    # Create a display dataframe with links
    display_df = pd.DataFrame()
    display_df['Date'] = df['Date']
    display_df['Time filter used'] = df['time_filter_used']
    
    # Add MISS, SONY, and GOA file link columns
    display_df['MISS Files'] = df.apply(
        lambda row: create_file_links(row['miss_folder_path'], row['miss_files_list'], 'MISS'), 
        axis=1
    )
    display_df['SONY Files'] = df.apply(
        lambda row: create_file_links(row['sony_folder_path'], row['sony_files_list'], 'SONY'), 
        axis=1
    )
    display_df['GOA Files'] = df.apply(
        lambda row: create_file_links(row['goa_folder_path'], row['goa_files_list'], 'GOA'), 
        axis=1
    )
    
    display_df['Comments'] = df['Comments']
    
    # Display as HTML table with clickable links
    html_table = display_df.to_html(escape=False, index=False, classes='table table-striped', justify='left')
    
    # Add CSS styling and JavaScript for interactivity with dark theme
    styled_html = f'''
<!DOCTYPE html>
<html>
<head>
    <title>GHOST Events Table</title>
    <meta charset="UTF-8">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1e1e2e 0%, #2d2d44 100%);
            color: #e0e0e0;
            padding: 30px;
            min-height: 100vh;
        }}
        
        /* Hide GOA Files column by default */
        .dataframe thead th:nth-child(5),
        .dataframe tbody td:nth-child(5) {{
            display: none;
        }}
        
        /* Show GOA Files column when visible class is added */
        .dataframe.goa-visible thead th:nth-child(5),
        .dataframe.goa-visible tbody td:nth-child(5) {{
            display: table-cell;
        }}
        
        /* Hide Comments column by default */
        .dataframe thead th:nth-child(6),
        .dataframe tbody td:nth-child(6) {{
            display: none;
        }}
        
        /* Show Comments column when visible class is added */
        .dataframe.comments-visible thead th:nth-child(6),
        .dataframe.comments-visible tbody td:nth-child(6) {{
            display: table-cell;
        }}
        
        /* Add toggle button styling */
        .comment-toggle {{
            display: inline-block;
            padding: 8px 16px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #ffffff;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.9em;
            font-weight: 600;
            margin-bottom: 15px;
            margin-right: 10px;
            box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
            transition: all 0.3s ease;
        }}
        
        .comment-toggle:hover {{
            background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.5);
            transform: translateY(-2px);
        }}
        
        .comment-toggle::before {{
            content: '▶ ';
            display: inline-block;
            transition: transform 0.3s ease;
        }}
        
        .comment-toggle.expanded::before {{
            content: '▼ ';
        }}
        
        .container {{
            max-width: 2400px;
            margin: 0 auto;
            background: rgba(30, 30, 46, 0.7);
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
            backdrop-filter: blur(10px);
        }}
        
        .info-banner {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-left: 5px solid #a78bfa;
            padding: 20px;
            margin-bottom: 30px;
            border-radius: 8px;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
        }}
        
        .info-banner h3 {{
            margin-top: 0;
            margin-bottom: 12px;
            color: #ffffff;
            font-size: 1.5em;
            font-weight: 600;
        }}
        
        .info-banner p {{
            color: #f0f0f0;
            line-height: 1.6;
        }}
        
        .info-banner ul {{
            margin: 10px 0 10px 20px;
            color: #f0f0f0;
        }}
        
        .info-banner li {{
            margin: 8px 0;
            line-height: 1.5;
        }}
        
        .info-banner em {{
            color: #d4d4d4;
            font-size: 0.9em;
        }}
        
        .main-layout {{
            display: flex;
            gap: 0;
            margin-top: 20px;
            position: relative;
        }}
        
        .table-container {{
            flex: 1;
            min-width: 300px;
            overflow-x: auto;
            padding-right: 15px;
        }}
        
        .resize-handle {{
            width: 10px;
            background: #667eea;
            cursor: col-resize;
            position: relative;
            flex-shrink: 0;
            transition: background 0.2s ease;
            border-radius: 4px;
            margin: 0 10px;
        }}
        
        .resize-handle:hover {{
            background: #764ba2;
        }}
        
        .resize-handle::before {{
            content: '⋮';
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            color: #ffffff;
            font-size: 1.2em;
            line-height: 0.5;
        }}
        
        .viewer-panel {{
            width: 50vw;
            min-width: 600px;
            max-width: 1200px;
            background: #2a2a3e;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
            position: sticky;
            top: 20px;
            max-height: calc(100vh - 40px);
            overflow-y: auto;
        }}
        
        .viewer-section {{
            margin-bottom: 30px;
        }}
        
        .viewer-section h3 {{
            color: #a78bfa;
            margin-bottom: 15px;
            font-size: 1.1em;
            border-bottom: 2px solid #667eea;
            padding-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .viewer-section h3 .section-title {{
            flex-shrink: 0;
        }}
        
        .viewer-filename {{
            color: #fbbf24;
            font-family: 'Courier New', monospace;
            font-size: 0.85em;
            font-weight: normal;
            word-break: break-all;
            flex: 1;
        }}
        
        .viewer-content {{
            background: #1e1e2e;
            border-radius: 6px;
            padding: 15px;
            display: flex;
            align-items: center;
            justify-content: center;
            border: 1px solid #667eea;
        }}
        
        #miss-viewer {{
            min-height: 310px;
        }}
        
        #sony-viewer {{
            height: 510px;
            min-height: 510px;
        }}
        
        /* GOA viewer section - hidden by default */
        #goa-viewer-section {{
            display: none;
        }}
        
        #goa-viewer-section.visible {{
            display: block;
        }}
        
        #goa-viewer {{
            height: 510px;
            min-height: 510px;
        }}
        
        .viewer-content img {{
            max-width: 100%;
            height: auto;
            border-radius: 4px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.5);
        }}
        
        /* Ensure GOA images match SONY image display size */
        #sony-viewer img,
        #goa-viewer img {{
            max-height: 480px;
            width: auto;
            max-width: 100%;
        }}
        
        .viewer-placeholder {{
            color: #6b7280;
            text-align: center;
            font-style: italic;
        }}
        
        .dataframe {{
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
            background: #2a2a3e;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        }}
        
        .dataframe thead {{
            background: linear-gradient(135deg, #4a4a6a 0%, #3a3a5a 100%);
        }}
        
        .dataframe thead th {{
            padding: 16px;
            text-align: left;
            font-weight: 600;
            color: #ffffff;
            border-bottom: 2px solid #667eea;
            font-size: 0.95em;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .dataframe tbody tr {{
            transition: all 0.3s ease;
        }}
        
        .dataframe tbody tr:nth-child(even) {{
            background: rgba(255, 255, 255, 0.03);
        }}
        
        .dataframe tbody tr:hover {{
            background: rgba(102, 126, 234, 0.15);
            transform: scale(1.01);
            box-shadow: 0 4px 8px rgba(102, 126, 234, 0.2);
        }}
        
        .dataframe tbody td {{
            padding: 14px 16px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            color: #d0d0d0;
            vertical-align: top;
        }}
        
        .dataframe td:nth-child(1) {{
            min-width: 120px;
            font-weight: 500;
            color: #a78bfa;
        }}
        
        /* MISS Files, SONY Files, and GOA Files columns */
        .dataframe td:nth-child(3),
        .dataframe td:nth-child(4),
        .dataframe td:nth-child(5) {{
            min-width: 250px;
        }}
        
        .dataframe a {{
            color: #60a5fa;
            text-decoration: none;
            transition: all 0.2s ease;
            border-bottom: 1px solid transparent;
            cursor: pointer;
        }}
        
        .dataframe a:hover {{
            color: #93c5fd;
            border-bottom: 1px solid #93c5fd;
        }}
        
        .dataframe a.selected {{
            color: #fbbf24;
            font-weight: bold;
        }}
        
        /* Scrollbar styling */
        ::-webkit-scrollbar {{
            width: 10px;
            height: 10px;
        }}
        
        ::-webkit-scrollbar-track {{
            background: #1e1e2e;
            border-radius: 5px;
        }}
        
        ::-webkit-scrollbar-thumb {{
            background: #667eea;
            border-radius: 5px;
        }}
        
        ::-webkit-scrollbar-thumb:hover {{
            background: #764ba2;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="info-banner">
            <h3>📈 GHOST Events Table</h3>
            <p><strong>How to use:</strong></p>
            <ul>
                <li>Click on any file in the MISS Files, SONY Files, or GOA Files columns to view it in the panel on the right</li>
                <li>MISS/MISS2 files will display their spectral plots 📈</li>
                <li>SONY and GOA files will display the images 📷</li>
                <li>Click the 'Show AllskyGOA' button to toggle the GOA Files column and viewer</li>
                <li>Click the 'Show Comments' button to toggle the Comments column</li>
            </ul>
            <p><em>Note: MISS plots are pre-generated and saved in the miss_plots folder.</em></p>
        </div>
        
        <button class="comment-toggle" id="goa-toggle">Show AllskyGOA</button>
        <button class="comment-toggle" id="comment-toggle">Show Comments</button>
        
        <div class="main-layout">
            <div class="table-container">
                {html_table}
            </div>
            
            <div class="resize-handle" id="resize-handle"></div>
            
            <div class="viewer-panel" id="viewer-panel">
                <div class="viewer-section">
                    <h3>
                        <span class="section-title">📈 MISS/MISS2 Spectral Plot</span>
                        <span class="viewer-filename" id="miss-filename"></span>
                    </h3>
                    <div class="viewer-content" id="miss-viewer">
                        <div class="viewer-placeholder">Click on a MISS file to view its spectral plot</div>
                    </div>
                </div>
                
                <div class="viewer-section">
                    <h3>
                        <span class="section-title">📷 SONY Image</span>
                        <span class="viewer-filename" id="sony-filename"></span>
                    </h3>
                    <div class="viewer-content" id="sony-viewer">
                        <div class="viewer-placeholder">Click on a SONY file to view the image</div>
                    </div>
                </div>
                
                <div class="viewer-section" id="goa-viewer-section">
                    <h3>
                        <span class="section-title">🌌 AllskyGOA Image</span>
                        <span class="viewer-filename" id="goa-filename"></span>
                    </h3>
                    <div class="viewer-content" id="goa-viewer">
                        <div class="viewer-placeholder">Click on a GOA file to view the image</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        document.addEventListener('DOMContentLoaded', function() {{
            const missViewer = document.getElementById('miss-viewer');
            const sonyViewer = document.getElementById('sony-viewer');
            const goaViewer = document.getElementById('goa-viewer');
            const missFilename = document.getElementById('miss-filename');
            const sonyFilename = document.getElementById('sony-filename');
            const goaFilename = document.getElementById('goa-filename');
            const goaViewerSection = document.getElementById('goa-viewer-section');
            
            // GOA toggle functionality
            const goaToggle = document.getElementById('goa-toggle');
            const dataframeTable = document.querySelector('.dataframe');
            
            goaToggle.addEventListener('click', function() {{
                dataframeTable.classList.toggle('goa-visible');
                goaViewerSection.classList.toggle('visible');
                this.classList.toggle('expanded');
                
                if (dataframeTable.classList.contains('goa-visible')) {{
                    this.textContent = 'Hide AllskyGOA';
                }} else {{
                    this.textContent = 'Show AllskyGOA';
                }}
            }});
            
            // Comment toggle functionality
            const commentToggle = document.getElementById('comment-toggle');
            
            commentToggle.addEventListener('click', function() {{
                dataframeTable.classList.toggle('comments-visible');
                this.classList.toggle('expanded');
                
                if (dataframeTable.classList.contains('comments-visible')) {{
                    this.textContent = 'Hide Comments';
                }} else {{
                    this.textContent = 'Show Comments';
                }}
            }});
            
            // Get all links in the table
            const allLinks = Array.from(document.querySelectorAll('.dataframe a'));
            let currentLinkIndex = -1;
            
            // Track currently selected link for each viewer type
            let selectedMissLink = null;
            let selectedSonyLink = null;
            let selectedGoaLink = null;
            
            // Resizable panel functionality
            const resizeHandle = document.getElementById('resize-handle');
            const viewerPanel = document.getElementById('viewer-panel');
            let isResizing = false;
            
            resizeHandle.addEventListener('mousedown', function(e) {{
                isResizing = true;
                document.body.style.cursor = 'col-resize';
                document.body.style.userSelect = 'none';
            }});
            
            document.addEventListener('mousemove', function(e) {{
                if (!isResizing) return;
                
                const containerRect = document.querySelector('.main-layout').getBoundingClientRect();
                const newWidth = containerRect.right - e.clientX;
                
                // Constrain width between min and max
                if (newWidth >= 600 && newWidth <= 1200) {{
                    viewerPanel.style.width = newWidth + 'px';
                }}
            }});
            
            document.addEventListener('mouseup', function() {{
                if (isResizing) {{
                    isResizing = false;
                    document.body.style.cursor = '';
                    document.body.style.userSelect = '';
                }}
            }});
            
            function displayFile(link) {{
                if (!link) return;
                
                const url = link.getAttribute('href');
                const filename = link.textContent.trim();
                
                // Update current index
                currentLinkIndex = allLinks.indexOf(link);
                
                // Check if it's a MISS/MISS2 plot (filename starts with MISS- or MISS2-)
                if (filename.startsWith('MISS-') || filename.startsWith('MISS2-')) {{
                    // Remove selected class from previously selected MISS link
                    if (selectedMissLink) {{
                        selectedMissLink.classList.remove('selected');
                    }}
                    
                    // Add selected class to new MISS link
                    link.classList.add('selected');
                    selectedMissLink = link;
                    
                    // Clean filename (remove emojis if present)
                    const cleanFilename = filename.replace(' 📈', '').replace(' 📊', '').trim();
                    
                    // Display filename and image in MISS viewer
                    missFilename.textContent = '- ' + cleanFilename;
                    missViewer.innerHTML = '<img src="' + url + '" alt="' + cleanFilename + '">';
                }} else if (filename.startsWith('C004_')) {{
                    // Remove selected class from previously selected GOA link
                    if (selectedGoaLink) {{
                        selectedGoaLink.classList.remove('selected');
                    }}
                    
                    // Add selected class to new GOA link
                    link.classList.add('selected');
                    selectedGoaLink = link;
                    
                    // GOA file (format: C004_YYYYMMDD_HHMM.jpg)
                    // Display filename and image in GOA viewer
                    goaFilename.textContent = '- ' + filename;
                    goaViewer.innerHTML = '<img src="' + url + '" alt="' + filename + '">';
                }} else {{
                    // Remove selected class from previously selected SONY link
                    if (selectedSonyLink) {{
                        selectedSonyLink.classList.remove('selected');
                    }}
                    
                    // Add selected class to new SONY link
                    link.classList.add('selected');
                    selectedSonyLink = link;
                    
                    // Display filename and image in SONY viewer
                    sonyFilename.textContent = '- ' + filename;
                    sonyViewer.innerHTML = '<img src="' + url + '" alt="' + filename + '">';
                }}
                
                // Scroll link into view
                link.scrollIntoView({{ behavior: 'smooth', block: 'nearest' }});
            }}
            
            // Click event listeners
            allLinks.forEach(link => {{
                link.addEventListener('click', function(e) {{
                    e.preventDefault();
                    displayFile(this);
                }});
            }});
            
            // Keyboard navigation
            document.addEventListener('keydown', function(e) {{
                if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {{
                    e.preventDefault();
                    
                    if (allLinks.length === 0) return;
                    
                    if (e.key === 'ArrowDown') {{
                        // Move to next file
                        currentLinkIndex = (currentLinkIndex + 1) % allLinks.length;
                    }} else if (e.key === 'ArrowUp') {{
                        // Move to previous file
                        currentLinkIndex = currentLinkIndex <= 0 ? allLinks.length - 1 : currentLinkIndex - 1;
                    }}
                    
                    displayFile(allLinks[currentLinkIndex]);
                }}
            }});
        }});
    </script>
</body>
</html>
'''
    
    # Save the HTML to a file
    with open(output_html, 'w', encoding='utf-8') as f:
        f.write(styled_html)
    
    print(f"\nHTML table saved to {output_html}")
    print(f"Open this file in a web browser to view the interactive table.")
    
    # Also save the display dataframe with all the data including file lists
    display_df.to_pickle('ghost_events_with_files.pkl')
    print(f"Display dataframe saved to ghost_events_with_files.pkl")
    
    return styled_html


if __name__ == '__main__':
    # Generate the HTML table
    # Set generate_plots=False if you don't want to regenerate MISS plots
    generate_html_table(generate_plots=True)

