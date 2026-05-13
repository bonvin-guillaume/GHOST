"""
This script processes GHOST events from GHOSTs_events.csv and finds corresponding
MISS, SONY, GOA, and BACC files for each event, saving the results to ghost_df.csv.

TODO:
- Add filtering logic when an event is close to midnight. At the moment, it will only find files for the day of the event.

@author: Guillaume Bonvin
"""

import os
import re
import numpy as np
import pandas as pd
from datetime import datetime, timedelta


# Input/output files
INPUT_CSV = 'march2026_updated_GHOSTs_events.csv'
OUTPUT_CSV = 'ghost_df.csv'

# Base directories for MISS-1/2 and SONY data
# On macOS use /Volumes/KHO when the KHO share is mounted in Finder
if os.name == 'posix':
    _KHO_BASE = '/Volumes/KHO'
else:
    _KHO_BASE = r'\\birkeland.unis.no\KHO'
MISS1_BASE_DIR = os.path.join(_KHO_BASE, 'MISS-1')
MISS2_BASE_DIR = os.path.join(_KHO_BASE, 'MISS-2')
SONY_QUICKLOOKS_BASE_DIR = os.path.join(_KHO_BASE, 'Sony', 'Quicklooks')
SONY_FALLBACK_BASE_DIR = os.path.join(_KHO_BASE, 'Sony')
BACC_BASE_DIR = r'C:\Users\guillaumeb\Documents\GHOST\BACC_frames'
GOA_BASE_DIR = '/Users/guillaume/GHOST/GOA'


def parse_time_string(time_str):
    """Parse various time formats and return a time object or None"""
    if pd.isna(time_str) or time_str == '' or time_str == '?':
        return None
    
    time_str = str(time_str).strip()
    
    # Try different time formats
    time_formats = [
        '%H:%M:%S',     # HH:MM:SS
        '%H:%M',        # HH:MM
        '%H:%M:%S.%f',  # HH:MM:SS.fff
    ]
    
    for fmt in time_formats:
        try:
            return datetime.strptime(time_str, fmt).time()
        except ValueError:
            continue
    
    return None


def extract_time_from_filename(filename):
    """Extract time from MISS, SONY, GOA, or BACC filename
    Supports formats:
    - MISS: MISS-YYYYMMDD-HHMMSS (e.g., MISS-20211126-002500.pgm)
    - MISS2: MISS2-YYYYMMDD-HHMMSS (e.g., MISS2-20241231-001215)
    - SONY: LYR-Sony-YYYYMMDD_HHMMSS (e.g., LYR-Sony-20160204_000018)
    - GOA: C004_YYYYMMDD_HHMM.jpg (e.g., C004_20250101_0706.jpg)
    - BACC: BACC_LYR_DDMMYYYY_HHMMSS (e.g., BACC_LYR_08122016_235121)
    """
    # Try MISS/MISS2 format: dash separator before time
    # Example: MISS-20211126-002500 or MISS2-20241231-001215
    pattern_miss = r'-\d{8}-(\d{2})(\d{2})(\d{2})'
    
    match = re.search(pattern_miss, filename)
    if match:
        h, m, s = int(match.group(1)), int(match.group(2)), int(match.group(3))
        # Validate that it's a reasonable time
        if 0 <= h < 24 and 0 <= m < 60 and 0 <= s < 60:
            try:
                return datetime.strptime(f"{h:02d}:{m:02d}:{s:02d}", '%H:%M:%S').time()
            except ValueError:
                pass
    
    # Try SONY format: underscore separator before time
    # Format: LYR-Sony-YYYYMMDD_HHMMSS (8 digits for date)
    pattern_sony = r'-\d{8}_(\d{2})(\d{2})(\d{2})'
    
    match = re.search(pattern_sony, filename)
    if match:
        h, m, s = int(match.group(1)), int(match.group(2)), int(match.group(3))
        # Validate that it's a reasonable time
        if 0 <= h < 24 and 0 <= m < 60 and 0 <= s < 60:
            try:
                return datetime.strptime(f"{h:02d}:{m:02d}:{s:02d}", '%H:%M:%S').time()
            except ValueError:
                pass
    
    # Try BACC format: BACC_LYR_DDMMYYYY_HHMMSS
    # Format: BACC_LYR_08122016_235121
    pattern_bacc = r'BACC_LYR_\d{8}_(\d{2})(\d{2})(\d{2})'
    
    match = re.search(pattern_bacc, filename)
    if match:
        h, m, s = int(match.group(1)), int(match.group(2)), int(match.group(3))
        # Validate that it's a reasonable time
        if 0 <= h < 24 and 0 <= m < 60 and 0 <= s < 60:
            try:
                return datetime.strptime(f"{h:02d}:{m:02d}:{s:02d}", '%H:%M:%S').time()
            except ValueError:
                pass
    
    # Try GOA format: C004_YYYYMMDD_HHMM
    # Format: C004_20250101_0706.jpg (only 4 digits for time: HHMM)
    pattern_goa = r'_\d{8}_(\d{2})(\d{2})'
    
    match = re.search(pattern_goa, filename)
    if match:
        h, m = int(match.group(1)), int(match.group(2))
        # Validate that it's a reasonable time
        if 0 <= h < 24 and 0 <= m < 60:
            try:
                return datetime.strptime(f"{h:02d}:{m:02d}:00", '%H:%M:%S').time()
            except ValueError:
                pass
    
    return None


def time_in_range(file_time, start_time, end_time, buffer_minutes):
    """Check if file_time is within the range (with optional buffer for spectrum time)"""
    if file_time is None:
        return False  # If can't parse file time, exclude it
    
    if start_time is None and end_time is None:
        return True  # No time constraints
    
    # For spectrum time (when start == end), add buffer
    if start_time == end_time:
        center = datetime.combine(datetime.today(), start_time)
        start_dt = center - timedelta(minutes=buffer_minutes)
        end_dt = center + timedelta(minutes=buffer_minutes)
        file_dt = datetime.combine(datetime.today(), file_time)
        return start_dt <= file_dt <= end_dt
    
    # For time range
    if start_time and end_time:
        file_dt = datetime.combine(datetime.today(), file_time)
        start_dt = datetime.combine(datetime.today(), start_time)
        end_dt = datetime.combine(datetime.today(), end_time)
        
        # Handle case where time range crosses midnight
        if end_dt < start_dt:
            return file_dt >= start_dt or file_dt <= end_dt
        else:
            return start_dt <= file_dt <= end_dt
    
    return True


def process_ghost_events(input_csv=None, output_csv=None, buffer_minutes=45):
    """
    Process GHOST events CSV file and find corresponding MISS, SONY, GOA, and BACC files.
    
    Args:
        input_csv: Path to input CSV file with GHOST events (default: INPUT_CSV)
        output_csv: Path to output CSV file with processed results (default: OUTPUT_CSV)
        buffer_minutes: Time buffer in minutes for spectrum time matching
    """
    if input_csv is None:
        input_csv = INPUT_CSV
    if output_csv is None:
        output_csv = OUTPUT_CSV
    # Read the GHOSTs events CSV file into a pandas DataFrame
    print(f"Reading {input_csv}...")
    df = pd.read_csv(input_csv, on_bad_lines='warn')
    
    # Forward fill empty Date values (rows with same date as previous row)
    df['Date'] = df['Date'].replace('', np.nan)
    df['Date'] = df['Date'].ffill()
    
    # Display basic information about the DataFrame
    print(f"DataFrame shape: {df.shape}")
    print(f"Column names: {df.columns.tolist()}")
    
    # Create new columns to store results
    df['MISS_folder_exists'] = False
    df['SONY_folder_exists'] = False
    df['GOA_folder_exists'] = False
    df['BACC_folder_exists'] = False
    df['files_found'] = 0
    df['miss_folder_path'] = ''
    df['sony_folder_path'] = ''
    df['goa_folder_path'] = ''
    df['bacc_folder_path'] = ''
    df['miss_files_found'] = 0
    df['sony_files_found'] = 0
    df['goa_files_found'] = 0
    df['bacc_files_found'] = 0
    df['sample_files'] = ''
    df['time_filter_used'] = ''
    df['miss_files_list'] = [[] for _ in range(len(df))]
    df['sony_files_list'] = [[] for _ in range(len(df))]
    df['goa_files_list'] = [[] for _ in range(len(df))]
    df['bacc_files_list'] = [[] for _ in range(len(df))]
    
    # Iterate through each row in the DataFrame
    for idx, row in df.iterrows():
        date_str = row['Date']
        
        # Skip if date is missing or NaN
        if pd.isna(date_str) or date_str == '':
            print(f"Row {idx}: No date provided, skipping")
            continue
        
        try:
            # Parse the date
            date = pd.to_datetime(date_str, format='%Y-%m-%d')
            year = date.strftime('%Y')
            month = date.strftime('%m')
            day = date.strftime('%d')
            
            # Use miss2_base_dir if date is after September 2024, otherwise use miss1_base_dir
            if date >= pd.Timestamp('2024-09-27'):
                miss_base_dir = MISS2_BASE_DIR
            else:
                miss_base_dir = MISS1_BASE_DIR
            
            # Create list of possible folder paths to check (MISS, Sony, GOA, and BACC)
            miss_folder_path = os.path.join(miss_base_dir, year, month, day)
            sony_quicklooks_path = os.path.join(SONY_QUICKLOOKS_BASE_DIR, year, month, day)
            sony_fallback_path = os.path.join(SONY_FALLBACK_BASE_DIR, year, month, day)
            if os.path.exists(sony_quicklooks_path):
                sony_folder_path = sony_quicklooks_path
            else:
                sony_folder_path = sony_fallback_path
            # GOA uses DD-MM-YYYY format for folder names
            goa_folder_path = os.path.join(GOA_BASE_DIR, f"{day}-{month}-{year}")
            # BACC uses YYYY-MM-DD format for folder names
            bacc_folder_path = os.path.join(BACC_BASE_DIR, f"{year}-{month}-{day}")
            
            # Store the paths separately
            df.at[idx, 'miss_folder_path'] = miss_folder_path
            df.at[idx, 'sony_folder_path'] = sony_folder_path
            df.at[idx, 'goa_folder_path'] = goa_folder_path
            df.at[idx, 'bacc_folder_path'] = bacc_folder_path
            
            # Check which folders exist
            miss_exists = os.path.exists(miss_folder_path)
            sony_exists = os.path.exists(sony_folder_path)
            goa_exists = os.path.exists(goa_folder_path)
            bacc_exists = os.path.exists(bacc_folder_path)
            
            # Store folder existence separately
            df.at[idx, 'MISS_folder_exists'] = miss_exists
            df.at[idx, 'SONY_folder_exists'] = sony_exists
            df.at[idx, 'GOA_folder_exists'] = goa_exists
            df.at[idx, 'BACC_folder_exists'] = bacc_exists
            
            existing_paths = []
            if miss_exists:
                existing_paths.append(('miss', miss_folder_path))
            if sony_exists:
                existing_paths.append(('sony', sony_folder_path))
            if goa_exists:
                existing_paths.append(('goa', goa_folder_path))
            if bacc_exists:
                existing_paths.append(('bacc', bacc_folder_path))
            
            # Parse time information
            spectrum_time = parse_time_string(row.get('spectrum time', ''))
            start_time = parse_time_string(row.get('Start time', ''))
            stop_time = parse_time_string(row.get('Stop time', ''))
            
            # Determine which time filter to use
            if start_time and stop_time:
                # Case 1: Both start and stop time provided
                filter_start = start_time
                filter_end = stop_time
                time_filter = f"range: {start_time} - {stop_time}"
            elif spectrum_time:
                # Case 2: Only spectrum time - use ±buffer_minutes window
                filter_start = spectrum_time
                filter_end = spectrum_time
                time_filter = f"spectrum time: {spectrum_time} (±{buffer_minutes} min)"
            elif start_time:
                # Case 3: Only start time - window is start_time to start_time + 3×buffer_minutes
                start_dt = datetime.combine(datetime.today(), start_time)
                end_dt = start_dt + timedelta(minutes=3 * buffer_minutes)
                filter_start = start_time
                filter_end = end_dt.time()
                time_filter = f"from: {start_time} to {filter_end} (+{3*buffer_minutes} min)"
            elif stop_time:
                # Case 4: Only stop time - window is stop_time - 3×buffer_minutes to stop_time
                end_dt = datetime.combine(datetime.today(), stop_time)
                start_dt = end_dt - timedelta(minutes=3 * buffer_minutes)
                filter_start = start_dt.time()
                filter_end = stop_time
                time_filter = f"from: {filter_start} (-{3*buffer_minutes} min) to {stop_time}"
            else:
                # Case 5: No time info - use whole day
                filter_start = None
                filter_end = None
                time_filter = "whole day (no time info)"
            
            df.at[idx, 'time_filter_used'] = time_filter
            
            # Check if any folders exist and process files from all existing folders
            if existing_paths:
                # Collect files separately from MISS, SONY, GOA, and BACC directories
                miss_files_all = []
                sony_files_all = []
                goa_files_all = []
                bacc_files_all = []
                
                for source_type, folder_path in existing_paths:
                    try:
                        if source_type == 'miss':
                            files_in_folder = [f for f in os.listdir(folder_path) if f.startswith('MISS')]
                            miss_files_all.extend(files_in_folder)
                        elif source_type == 'sony':
                            files_in_folder = [f for f in os.listdir(folder_path) if f.startswith('LYR-Sony-')]
                            sony_files_all.extend(files_in_folder)
                        elif source_type == 'goa':
                            # Get all .jpg files in GOA folder (format: C004_YYYYMMDD_HHMM.jpg)
                            files_in_folder = [f for f in os.listdir(folder_path) 
                                             if f.endswith('.jpg') and os.path.isfile(os.path.join(folder_path, f))]
                            goa_files_all.extend(files_in_folder)
                        elif source_type == 'bacc':
                            # Get all BACC files in folder (format: BACC_LYR_DDMMYYYY_HHMMSS_NNNN)
                            files_in_folder = [f for f in os.listdir(folder_path) 
                                             if f.startswith('BACC_LYR_') and os.path.isfile(os.path.join(folder_path, f))]
                            bacc_files_all.extend(files_in_folder)
                    except Exception as e:
                        print(f"Row {idx} ({date_str}): Error reading {folder_path}: {e}")
                
                # Filter MISS files by time
                miss_files_filtered = []
                for f in miss_files_all:
                    file_time = extract_time_from_filename(f)
                    if time_in_range(file_time, filter_start, filter_end, buffer_minutes):
                        miss_files_filtered.append(f)
                
                # Filter SONY files by time
                sony_files_filtered = []
                for f in sony_files_all:
                    file_time = extract_time_from_filename(f)
                    if time_in_range(file_time, filter_start, filter_end, buffer_minutes):
                        sony_files_filtered.append(f)
                
                # Filter BACC files by time
                bacc_files_filtered = []
                for f in bacc_files_all:
                    file_time = extract_time_from_filename(f)
                    if time_in_range(file_time, filter_start, filter_end, buffer_minutes):
                        bacc_files_filtered.append(f)
                
                # Use filtered files if time filter was applied, otherwise use all
                miss_files = miss_files_filtered if miss_files_filtered or (filter_start or filter_end) else miss_files_all
                sony_files = sony_files_filtered if sony_files_filtered or (filter_start or filter_end) else sony_files_all
                goa_files = goa_files_all  # no time filter for GOA
                bacc_files = bacc_files_filtered if bacc_files_filtered or (filter_start or filter_end) else bacc_files_all
                
                # Store counts separately
                df.at[idx, 'miss_files_found'] = len(miss_files)
                df.at[idx, 'sony_files_found'] = len(sony_files)
                df.at[idx, 'goa_files_found'] = len(goa_files)
                df.at[idx, 'bacc_files_found'] = len(bacc_files)
                df.at[idx, 'files_found'] = len(miss_files) + len(sony_files) + len(goa_files) + len(bacc_files)
                
                # Store the actual filtered file lists
                df.at[idx, 'miss_files_list'] = sorted(miss_files)
                df.at[idx, 'sony_files_list'] = sorted(sony_files)
                df.at[idx, 'goa_files_list'] = sorted(goa_files)
                df.at[idx, 'bacc_files_list'] = sorted(bacc_files)
                
                # Store sample files (combined)
                all_files = miss_files + sony_files + goa_files + bacc_files
                if len(all_files) > 0:
                    sample = ', '.join(all_files[:3])
                    if len(all_files) > 3:
                        sample += f' ... ({len(all_files)} total)'
                    df.at[idx, 'sample_files'] = sample
                    
                # Print summary
                summary_parts = []
                if len(miss_files_all) > 0:
                    summary_parts.append(f"MISS: {len(miss_files)}/{len(miss_files_all)}")
                if len(sony_files_all) > 0:
                    summary_parts.append(f"SONY: {len(sony_files)}/{len(sony_files_all)}")
                if len(goa_files_all) > 0:
                    summary_parts.append(f"GOA: {len(goa_files)}/{len(goa_files_all)}")
                if len(bacc_files_all) > 0:
                    summary_parts.append(f"BACC: {len(bacc_files)}/{len(bacc_files_all)}")
                
                summary_str = ', '.join(summary_parts) if summary_parts else "no files"
                print(f"Row {idx} ({date_str}): {summary_str} files match time filter [{time_filter}]")
            else:
                print(f"Row {idx} ({date_str}): Folders do NOT exist")
                
        except Exception as e:
            print(f"Row {idx}: Error processing date '{date_str}': {e}")
    
    # Save DataFrame to CSV
    df.to_csv(output_csv, index=False)
    print(f"\n{'='*80}")
    print("SUMMARY:")
    print(f"Total entries: {len(df)}")
    print(f"Entries with valid dates: {df['Date'].notna().sum()}")
    print(f"MISS folders found: {df['MISS_folder_exists'].sum()}")
    print(f"SONY folders found: {df['SONY_folder_exists'].sum()}")
    print(f"GOA folders found: {df['GOA_folder_exists'].sum()}")
    print(f"BACC folders found: {df['BACC_folder_exists'].sum()}")
    print(f"Total MISS files found: {df['miss_files_found'].sum()}")
    print(f"Total SONY files found: {df['sony_files_found'].sum()}")
    print(f"Total GOA files found: {df['goa_files_found'].sum()}")
    print(f"Total BACC files found: {df['bacc_files_found'].sum()}")
    print(f"{'='*80}")
    print(f"\nDataFrame saved to {output_csv}")
    print(f"Shape: {df.shape}")
    
    return df


if __name__ == '__main__':
    # Process the events
    df = process_ghost_events()

