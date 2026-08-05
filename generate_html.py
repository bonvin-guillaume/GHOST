"""
This script generates an interactive HTML table from the processed ghost_df.csv file.
The HTML table includes clickable links to MISS, SONY, and GOA files with inline viewers.

@author: Guillaume Bonvin
"""

import os
import re
import ast
import pandas as pd
from datetime import datetime, timezone


def _parse_timestamp_ms(filename):
    """Parse a Unix millisecond timestamp from a filename.

    Handles:
      - YYYYMMDD_HHMMSS  (SONY)
      - YYYYMMDD-HHMMSS  (MISS, MISS2 — e.g. MISS-20200228-030500.pgm)
      - YYYYMMDD_HHMM    (GOA)
    Returns None if no pattern is found.
    """
    # Underscore separator: SONY (YYYYMMDD_HHMMSS)
    m = re.search(r'(\d{8})_(\d{6})', filename)
    if m:
        try:
            dt = datetime.strptime(m.group(1) + m.group(2), '%Y%m%d%H%M%S')
            return int(dt.replace(tzinfo=timezone.utc).timestamp() * 1000)
        except ValueError:
            pass
    # Dash separator: MISS / MISS2 (YYYYMMDD-HHMMSS)
    m = re.search(r'(\d{8})-(\d{6})', filename)
    if m:
        try:
            dt = datetime.strptime(m.group(1) + m.group(2), '%Y%m%d%H%M%S')
            return int(dt.replace(tzinfo=timezone.utc).timestamp() * 1000)
        except ValueError:
            pass
    # Underscore separator, 4-digit time: GOA (YYYYMMDD_HHMM)
    m = re.search(r'(\d{8})_(\d{4})', filename)
    if m:
        try:
            dt = datetime.strptime(m.group(1) + m.group(2), '%Y%m%d%H%M')
            return int(dt.replace(tzinfo=timezone.utc).timestamp() * 1000)
        except ValueError:
            pass
    return None


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
        
        # Build a data-timestamp attribute when the filename carries a parseable time
        ts = _parse_timestamp_ms(filename)
        ts_attr = f' data-timestamp="{ts}"' if ts is not None else ''

        # For MISS .pgm files, create links to the generated plot images
        if label == 'MISS' and filename.endswith('.pgm') and filename.startswith('MISS-'):
            # Link to the generated plot PNG (MISS-1)
            plot_filename = filename.replace('.pgm', '_plot.png')
            plot_path = os.path.join('MISS_plots', plot_filename)
            
            # Convert to file:// URL for the plot image
            plot_url = 'file:///' + os.path.abspath(plot_path).replace('\\', '/')
            
            # Create link with filename that opens the plot
            links.append(f'<a href="{plot_url}" target="_blank" title="View spectral plot"{ts_attr}>{filename} 📊</a>')
        # For MISS2 files, create links to the generated plot images
        elif label == 'MISS' and filename.startswith('MISS2-'):
            # Link to the generated plot PNG (MISS-2)
            plot_filename = filename.replace('.png', '_plot.png')
            plot_path = os.path.join('MISS_plots', plot_filename)
            
            # Convert to file:// URL for the plot image
            plot_url = 'file:///' + os.path.abspath(plot_path).replace('\\', '/')
            
            # Create link with filename that opens the plot
            links.append(f'<a href="{plot_url}" target="_blank" title="View spectral plot"{ts_attr}>{filename} 📈</a>')
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
            links.append(f'<a href="{file_url}" target="_blank"{ts_attr}>{filename}</a>')
    
    # Join all links with line breaks
    links_html = '<br>'.join(links)
    
    # Put in a scrollable div with fixed height
    # Show file count at the top
    # Width set to fit one filename (about 240px for typical filename length)
    # Max-height set to show ~5 files at a time (120px)
    return f'<div style="width: 240px; font-size: 0.9em;"><div style="font-weight: bold; margin-bottom: 5px; color: #a0a0a0;">{len(file_list)} file(s)</div><div style="max-height: 120px; overflow-y: auto; border: 1px solid rgba(255, 255, 255, 0.1); padding: 5px; white-space: nowrap; border-radius: 4px; background: rgba(0, 0, 0, 0.2);">{links_html}</div></div>'


def generate_html_table(input_csv='ghost_df.csv', output_html='interactive_GHOST_tool.html'):
    """
    Generate an interactive HTML table from the processed ghost_df.csv file.
    
    Args:
        input_csv: Path to input CSV file with processed GHOST events
        output_html: Path to output HTML file
    """
    # Read the processed CSV file
    print(f"Reading {input_csv}...")
    df = pd.read_csv(input_csv)
    
    print(f"DataFrame shape: {df.shape}")
    
    # Create a display dataframe with links
    display_df = pd.DataFrame()
    display_df['Date'] = df['Date']
    display_df['Time filter used'] = df['time_filter_used']
    display_df['Suspected GHOST'] = df['spectrum time']
    
    # Add MISS, SONY, GOA, and BACC file link columns
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
    display_df['BACC Files'] = df.apply(
        lambda row: create_file_links(row['bacc_folder_path'], row['bacc_files_list'], 'BACC'), 
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
        
        /* Hide Suspected GHOST column by default */
        .dataframe thead th:nth-child(3),
        .dataframe tbody td:nth-child(3) {{
            display: none;
        }}
        
        /* Show Suspected GHOST column when visible class is added */
        .dataframe.ghost-visible thead th:nth-child(3),
        .dataframe.ghost-visible tbody td:nth-child(3) {{
            display: table-cell;
        }}
        
        /* Hide GOA Files column by default */
        .dataframe thead th:nth-child(6),
        .dataframe tbody td:nth-child(6) {{
            display: none;
        }}
        
        /* Show GOA Files column when visible class is added */
        .dataframe.goa-visible thead th:nth-child(6),
        .dataframe.goa-visible tbody td:nth-child(6) {{
            display: table-cell;
        }}
        
        /* Hide BACC Files column by default */
        .dataframe thead th:nth-child(7),
        .dataframe tbody td:nth-child(7) {{
            display: none;
        }}
        
        /* Show BACC Files column when visible class is added */
        .dataframe.bacc-visible thead th:nth-child(7),
        .dataframe.bacc-visible tbody td:nth-child(7) {{
            display: table-cell;
        }}
        
        /* Hide Comments column by default */
        .dataframe thead th:nth-child(8),
        .dataframe tbody td:nth-child(8) {{
            display: none;
        }}
        
        /* Show Comments column when visible class is added */
        .dataframe.comments-visible thead th:nth-child(8),
        .dataframe.comments-visible tbody td:nth-child(8) {{
            display: table-cell;
        }}
        
        /* Add checkbox control styling */
        .column-controls {{
            display: flex;
            gap: 25px;
            margin-bottom: 0;
            padding: 15px;
            background: rgba(102, 126, 234, 0.1);
            border-radius: 8px;
            border: 1px solid rgba(102, 126, 234, 0.3);
            backdrop-filter: blur(10px);
            background: rgba(30, 30, 46, 0.95);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
            flex-shrink: 0;
        }}
        
        .checkbox-label {{
            display: inline-flex;
            align-items: center;
            cursor: pointer;
            user-select: none;
            font-size: 0.95em;
            font-weight: 500;
            color: #e0e0e0;
            transition: color 0.2s ease;
        }}
        
        .checkbox-label:hover {{
            color: #a78bfa;
        }}
        
        .checkbox-label input[type="checkbox"] {{
            width: 18px;
            height: 18px;
            margin-right: 10px;
            cursor: pointer;
            accent-color: #667eea;
        }}
        
        .checkbox-label input[type="checkbox"]:checked {{
            accent-color: #764ba2;
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
            padding-right: 15px;
            position: relative;
            display: flex;
            flex-direction: column;
            max-height: calc(100vh - 40px);
        }}
        
        .table-wrapper {{
            flex: 1;
            overflow-x: auto;
            overflow-y: auto;
            position: relative;
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
        
        /* Grid container for viewers - switches between 1 and 2 columns */
        .viewers-grid {{
            display: grid;
            grid-template-columns: 1fr;
            gap: 15px;
            align-items: start;
        }}
        
        /* Two-column layout when panel is wide enough and multiple sources selected */
        .viewer-panel.two-column .viewers-grid {{
            grid-template-columns: 1fr 1fr;
        }}
        
        /* Ensure MISS viewer spans full width in two-column mode */
        .viewer-panel.two-column .viewer-section:first-child {{
            grid-column: 1 / -1;
        }}
        
        .viewer-section {{
            margin-bottom: 0;
            min-width: 0;
            display: flex;
            flex-direction: column;
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
        
        #miss-viewer img {{
            max-height: 100%;
            width: auto;
            max-width: 100%;
            object-fit: contain;
        }}
        
        #sony-viewer {{
            min-height: 410px;
            overflow: auto;
        }}
        
        /* GOA viewer section - hidden by default */
        #goa-viewer-section {{
            display: none;
        }}
        
        #goa-viewer-section.visible {{
            display: block;
        }}
        
        #goa-viewer {{
            min-height: 410px;
            overflow: auto;
        }}
        
        /* BACC viewer section - hidden by default */
        #bacc-viewer-section {{
            display: none;
        }}
        
        #bacc-viewer-section.visible {{
            display: block;
        }}
        
        #bacc-viewer {{
            min-height: 410px;
            overflow: auto;
        }}
        
        .viewer-content img {{
            max-width: 100%;
            height: auto;
            border-radius: 4px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.5);
        }}
        
        /* Ensure SONY, GOA, and BACC images scale with panel width */
        #sony-viewer img,
        #goa-viewer img,
        #bacc-viewer img {{
            display: block;
            width: 100%;
            height: auto;
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
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        }}
        
        .dataframe thead {{
            background: linear-gradient(135deg, #4a4a6a 0%, #3a3a5a 100%);
            position: relative;
            z-index: 98;
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
            position: sticky;
            top: 0;
            z-index: 99;
            background: linear-gradient(135deg, #4a4a6a 0%, #3a3a5a 100%);
            backdrop-filter: blur(10px);
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
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
        
        /* MISS Files, SONY Files, GOA Files, and BACC Files columns */
        .dataframe td:nth-child(4),
        .dataframe td:nth-child(5),
        .dataframe td:nth-child(6),
        .dataframe td:nth-child(7) {{
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
                <li>Click on any file in the MISS Files, SONY Files, GOA Files, or BACC Files columns to view it in the panel on the right</li>
                <li>MISS/MISS2 files will display their spectral plots 📈</li>
                <li>SONY, GOA, and BACC files will display the images 📷</li>
                <li>Use the checkboxes below to toggle the Suspected GHOST, GOA Files, BACC Files, and Comments columns</li>
            </ul>
            <p><em>Note: MISS plots are pre-generated and saved in the MISS_plots folder.</em></p>
        </div>
        
        <div class="main-layout">
            <div class="table-container">
                <div class="column-controls">
                    <label class="checkbox-label">
                        <input type="checkbox" id="ghost-checkbox">
                        <span>Show suspected GHOST</span>
                    </label>
                    <label class="checkbox-label">
                        <input type="checkbox" id="goa-checkbox">
                        <span>Show AllskyGOA Files</span>
                    </label>
                    <label class="checkbox-label">
                        <input type="checkbox" id="bacc-checkbox">
                        <span>Show BACC Files</span>
                    </label>
                    <label class="checkbox-label">
                        <input type="checkbox" id="comment-checkbox">
                        <span>Show Comments</span>
                    </label>
                </div>
                <div class="table-wrapper">
                    {html_table}
                </div>
            </div>
            
            <div class="resize-handle" id="resize-handle"></div>
            
            <div class="viewer-panel" id="viewer-panel">
                <div class="viewers-grid">
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
                    
                    <div class="viewer-section" id="bacc-viewer-section">
                        <h3>
                            <span class="section-title">📷 BACC Image</span>
                            <span class="viewer-filename" id="bacc-filename"></span>
                        </h3>
                        <div class="viewer-content" id="bacc-viewer">
                            <div class="viewer-placeholder">Click on a BACC file to view the image</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // Load an image into a viewer while freezing its height to avoid a
        // collapse-then-expand flash during the transition.
        function loadViewerImage(viewer, url, alt) {{
            viewer.style.height = viewer.offsetHeight + 'px';
            const img = new Image();
            img.alt = alt;
            img.onload = function() {{ viewer.style.height = ''; }};
            img.src = url;
            viewer.innerHTML = '';
            viewer.appendChild(img);
        }}

        document.addEventListener('DOMContentLoaded', function() {{
            const missViewer = document.getElementById('miss-viewer');
            const sonyViewer = document.getElementById('sony-viewer');
            const goaViewer = document.getElementById('goa-viewer');
            const baccViewer = document.getElementById('bacc-viewer');
            const missFilename = document.getElementById('miss-filename');
            const sonyFilename = document.getElementById('sony-filename');
            const goaFilename = document.getElementById('goa-filename');
            const baccFilename = document.getElementById('bacc-filename');
            const goaViewerSection = document.getElementById('goa-viewer-section');
            const baccViewerSection = document.getElementById('bacc-viewer-section');
            
            // Get dataframe table reference
            const dataframeTable = document.querySelector('.dataframe');
            
            // Suspected GHOST checkbox functionality
            const ghostCheckbox = document.getElementById('ghost-checkbox');
            
            ghostCheckbox.addEventListener('change', function() {{
                if (this.checked) {{
                    dataframeTable.classList.add('ghost-visible');
                }} else {{
                    dataframeTable.classList.remove('ghost-visible');
                }}
            }});
            
            // GOA checkbox functionality
            const goaCheckbox = document.getElementById('goa-checkbox');
            
            goaCheckbox.addEventListener('change', function() {{
                if (this.checked) {{
                    dataframeTable.classList.add('goa-visible');
                    goaViewerSection.classList.add('visible');
                }} else {{
                    dataframeTable.classList.remove('goa-visible');
                    goaViewerSection.classList.remove('visible');
                }}
                updateViewerLayout();
            }});
            
            // BACC checkbox functionality
            const baccCheckbox = document.getElementById('bacc-checkbox');
            
            baccCheckbox.addEventListener('change', function() {{
                if (this.checked) {{
                    dataframeTable.classList.add('bacc-visible');
                    baccViewerSection.classList.add('visible');
                }} else {{
                    dataframeTable.classList.remove('bacc-visible');
                    baccViewerSection.classList.remove('visible');
                }}
                updateViewerLayout();
            }});
            
            // Comment checkbox functionality
            const commentCheckbox = document.getElementById('comment-checkbox');
            
            commentCheckbox.addEventListener('change', function() {{
                if (this.checked) {{
                    dataframeTable.classList.add('comments-visible');
                }} else {{
                    dataframeTable.classList.remove('comments-visible');
                }}
            }});
            
            // Get all links in the table
            const allLinks = Array.from(document.querySelectorAll('.dataframe a'));
            let currentLinkIndex = -1;
            
            // Track currently selected link for each viewer type
            let selectedMissLink = null;
            let selectedSonyLink = null;
            let selectedGoaLink = null;
            let selectedBaccLink = null;
            
            // Function to update layout based on panel width and visible sources
            function updateViewerLayout() {{
                const panelWidth = viewerPanel.offsetWidth;
                const visibleSourcesCount = 2 + (goaCheckbox.checked ? 1 : 0) + (baccCheckbox.checked ? 1 : 0);
                
                // Enable two-column layout if:
                // 1. More than 2 sources are visible (GOA or BACC checked)
                // 2. Panel width is at least 900px
                if (visibleSourcesCount > 2 && panelWidth >= 900) {{
                    viewerPanel.classList.add('two-column');
                }} else {{
                    viewerPanel.classList.remove('two-column');
                }}
            }}
            
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
                    updateViewerLayout();
                }}
            }});
            
            document.addEventListener('mouseup', function() {{
                if (isResizing) {{
                    isResizing = false;
                    document.body.style.cursor = '';
                    document.body.style.userSelect = '';
                }}
            }});
            
            // Find the link whose timestamp is the largest value <= floorTs.
            // Implements the floor/truncation rule robustly even when file
            // timestamps have minor offsets from the exact boundary.
            function _findFloor(links, floorTs) {{
                let best = null;
                let bestTs = -Infinity;
                links.forEach(function(l) {{
                    const t = parseInt(l.getAttribute('data-timestamp'), 10);
                    if (!isNaN(t) && t <= floorTs) {{
                        if (t > bestTs) {{
                            bestTs = t;
                            best = l;
                        }}
                    }}
                }});
                return best;
            }}

            // Find the link whose timestamp is the smallest value >= ceilTs.
            // Used when syncing from GOA: never show a file that happened before
            // the selected GOA image.
            function _findCeiling(links, ceilTs) {{
                let best = null;
                let bestTs = Infinity;
                links.forEach(function(l) {{
                    const t = parseInt(l.getAttribute('data-timestamp'), 10);
                    if (!isNaN(t) && t >= ceilTs) {{
                        if (t < bestTs) {{
                            bestTs = t;
                            best = l;
                        }}
                    }}
                }});
                return best;
            }}

            // When a SONY file is shown, update MISS (col 4, cells[3]) and GOA (col 6, cells[5])
            // using a floor/truncation rule: show the frame whose timestamp equals
            // floor(T_sony, 1 min) for MISS and floor(T_sony, 2 min) for GOA.
            function syncViewersToSony(sonyLink) {{
                const ts = parseInt(sonyLink.getAttribute('data-timestamp'), 10);
                if (isNaN(ts)) return;

                const row = sonyLink.closest('tr');
                if (!row) return;

                const cells = row.querySelectorAll('td');

                // floor to 1-minute boundary for MISS (60 000 ms)
                const missFloorTs = Math.floor(ts / 60000) * 60000;
                // floor to 2-minute boundary for GOA (120 000 ms)
                const goaFloorTs  = Math.floor(ts / 120000) * 120000;

                // MISS Files are in the 4th column (0-based index 3)
                if (cells[3]) {{
                    const missLinks = Array.from(cells[3].querySelectorAll('a[data-timestamp]'));
                    const floorMiss = _findFloor(missLinks, missFloorTs);
                    if (floorMiss) displayFile(floorMiss, false);
                }}

                // GOA Files are in the 6th column (0-based index 5)
                if (cells[5]) {{
                    const goaLinks = Array.from(cells[5].querySelectorAll('a[data-timestamp]'));
                    const floorGoa = _findFloor(goaLinks, goaFloorTs);
                    if (floorGoa) displayFile(floorGoa, false);
                }}
            }}

            // When a GOA image is shown, update MISS (col 4, cells[3]) and SONY (col 5, cells[4])
            // using a ceiling rule: show the nearest frame whose timestamp is >= the GOA timestamp
            // so that neither SONY nor MISS files that happened before the GOA image are shown.
            function syncViewersToGoa(goaLink) {{
                const ts = parseInt(goaLink.getAttribute('data-timestamp'), 10);
                if (isNaN(ts)) return;

                const row = goaLink.closest('tr');
                if (!row) return;

                const cells = row.querySelectorAll('td');

                // MISS Files are in the 4th column (0-based index 3)
                if (cells[3]) {{
                    const missLinks = Array.from(cells[3].querySelectorAll('a[data-timestamp]'));
                    const ceilMiss = _findCeiling(missLinks, ts);
                    if (ceilMiss) displayFile(ceilMiss, false);
                }}

                // SONY Files are in the 5th column (0-based index 4)
                if (cells[4]) {{
                    const sonyLinks = Array.from(cells[4].querySelectorAll('a[data-timestamp]'));
                    const ceilSony = _findCeiling(sonyLinks, ts);
                    if (ceilSony) displayFile(ceilSony, false);
                }}
            }}

            // sync=true  → user-initiated action: update keyboard index, scroll link into view,
            //              and trigger cross-viewer sync when a SONY file is shown.
            // sync=false → programmatic sync call: skip those side-effects to avoid loops.
            function displayFile(link, sync) {{
                if (!link) return;
                if (sync === undefined) sync = true;
                
                const url = link.getAttribute('href');
                const filename = link.textContent.trim();
                
                // Only update keyboard navigation index for user-initiated actions
                if (sync) {{
                    currentLinkIndex = allLinks.indexOf(link);
                }}
                
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
                    loadViewerImage(missViewer, url, cleanFilename);
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
                    loadViewerImage(goaViewer, url, filename);
                    
                    // Sync SONY and MISS viewers to the closest frame at or after this GOA image
                    if (sync) {{
                        syncViewersToGoa(link);
                    }}
                }} else if (filename.startsWith('BACC_LYR_')) {{
                    // Remove selected class from previously selected BACC link
                    if (selectedBaccLink) {{
                        selectedBaccLink.classList.remove('selected');
                    }}
                    
                    // Add selected class to new BACC link
                    link.classList.add('selected');
                    selectedBaccLink = link;
                    
                    // BACC file (format: BACC_LYR_DDMMYYYY_HHMMSS.png)
                    // Display filename and image in BACC viewer
                    baccFilename.textContent = '- ' + filename;
                    loadViewerImage(baccViewer, url, filename);
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
                    loadViewerImage(sonyViewer, url, filename);
                    
                    // Sync GOA and MISS viewers to the closest frame in time
                    if (sync) {{
                        syncViewersToSony(link);
                    }}
                }}
                
                // Scroll link into view only for user-initiated actions
                if (sync) {{
                    link.scrollIntoView({{ behavior: 'smooth', block: 'nearest' }});
                }}
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
            
            // Update layout on window resize
            window.addEventListener('resize', updateViewerLayout);
            
            // Initial layout check
            updateViewerLayout();
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
    
    return styled_html


if __name__ == '__main__':
    # Generate the HTML table
    generate_html_table()

