"""
Script to rename BACC files by updating the time information and removing the index.

Original filename format: BACC_LYR_DDMMYYYY_HHMMSS_XXXX.png
New filename format: BACC_LYR_DDMMYYYY_HHMMSS.png

The time is updated based on the index using a (25, 25, 26) second pattern.
"""

import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict


def parse_bacc_filename(filename):
    """
    Parse a BACC filename and extract date, time, and index.
    
    Args:
        filename: String like 'BACC_LYR_08122016_004028_0001.png'
    
    Returns:
        dict with 'date_str', 'time_str', 'index', 'extension' or None if invalid
    """
    pattern = r'BACC_LYR_(\d{8})_(\d{6})_(\d{4})\.(.+)'
    match = re.match(pattern, filename)
    
    if match:
        return {
            'date_str': match.group(1),
            'time_str': match.group(2),
            'index': int(match.group(3)),
            'extension': match.group(4)
        }
    return None


def calculate_time_offset(index):
    """
    Calculate the total time offset in seconds for a given index.
    The pattern is: 25, 25, 26 seconds, repeating.
    
    Args:
        index: File index (1-based)
    
    Returns:
        Total seconds to add to the base time
    """
    if index == 1:
        return 0
    
    # Pattern: [25, 25, 26] repeating
    pattern = [25, 25, 26]
    total_seconds = 0
    
    for i in range(1, index):
        # (i-1) % 3 gives us the position in the pattern (0, 1, or 2)
        increment = pattern[(i - 1) % 3]
        total_seconds += increment
    
    return total_seconds


def add_seconds_to_datetime(date_str, time_str, seconds):
    """
    Add seconds to a date/time string, handling day rollover.
    
    Args:
        date_str: Date string in DDMMYYYY format
        time_str: Time string in HHMMSS format
        seconds: Number of seconds to add
    
    Returns:
        Tuple of (new_date_str, new_time_str) in DDMMYYYY and HHMMSS formats
    """
    # Parse the date string (DDMMYYYY)
    day = int(date_str[0:2])
    month = int(date_str[2:4])
    year = int(date_str[4:8])
    
    # Parse the time string (HHMMSS)
    hours = int(time_str[0:2])
    minutes = int(time_str[2:4])
    secs = int(time_str[4:6])
    
    # Create a datetime object
    dt = datetime(year, month, day, hours, minutes, secs)
    
    # Add the seconds
    dt_new = dt + timedelta(seconds=seconds)
    
    # Format back to DDMMYYYY and HHMMSS
    new_date_str = dt_new.strftime('%d%m%Y')
    new_time_str = dt_new.strftime('%H%M%S')
    
    return new_date_str, new_time_str


def rename_bacc_files(directory, dry_run=True):
    """
    Rename BACC files in the specified directory.
    
    Args:
        directory: Path to directory containing BACC files
        dry_run: If True, only print what would be done without renaming
    """
    directory_path = Path(directory)
    
    if not directory_path.exists():
        print(f"Error: Directory '{directory}' does not exist!")
        return
    
    # Group files by date and base time
    file_groups = defaultdict(list)
    
    # Find all BACC files
    for file in directory_path.glob('BACC_LYR_*.png'):
        parsed = parse_bacc_filename(file.name)
        if parsed:
            key = (parsed['date_str'], parsed['time_str'])
            file_groups[key].append({
                'filename': file.name,
                'parsed': parsed,
                'path': file
            })
    
    # Sort each group by index
    for key in file_groups:
        file_groups[key].sort(key=lambda x: x['parsed']['index'])
    
    # Process each group
    total_files = 0
    renamed_count = 0
    
    for (date_str, base_time_str), files in sorted(file_groups.items()):
        print(f"\nProcessing group: Date={date_str}, Base Time={base_time_str}")
        print(f"  Files in group: {len(files)}")
        
        for file_info in files:
            parsed = file_info['parsed']
            index = parsed['index']
            
            # Calculate the time offset
            offset_seconds = calculate_time_offset(index)
            
            # Calculate the new date and time (handles day rollover)
            new_date_str, new_time_str = add_seconds_to_datetime(date_str, base_time_str, offset_seconds)
            
            # Create new filename (without index)
            new_filename = f"BACC_LYR_{new_date_str}_{new_time_str}.{parsed['extension']}"
            
            old_path = file_info['path']
            new_path = directory_path / new_filename
            
            total_files += 1
            
            # Show date change indicator if date changed
            date_indicator = f" [DATE CHANGED: {date_str}->{new_date_str}]" if new_date_str != date_str else ""
            
            if dry_run:
                print(f"  [{index:04d}] {file_info['filename']} -> {new_filename} (+{offset_seconds}s){date_indicator}")
            else:
                # Check if target file already exists
                if new_path.exists():
                    print(f"  WARNING: Target file already exists: {new_filename}")
                    print(f"           Skipping {file_info['filename']}")
                else:
                    old_path.rename(new_path)
                    renamed_count += 1
                    print(f"  [{index:04d}] Renamed: {file_info['filename']} -> {new_filename}{date_indicator}")
    
    print(f"\n{'DRY RUN ' if dry_run else ''}Summary:")
    print(f"  Total files processed: {total_files}")
    if not dry_run:
        print(f"  Successfully renamed: {renamed_count}")
        print(f"  Skipped: {total_files - renamed_count}")


def main():
    """Main function to run the script."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Rename BACC files by updating time and removing index in all subdirectories'
    )
    parser.add_argument(
        '--execute',
        action='store_true',
        help='Actually rename the files (default is dry-run mode)'
    )
    parser.add_argument(
        '--base-dir',
        default=r'C:\Users\guillaumeb\Documents\GHOST\BACC_frames',
        help='Base directory containing subdirectories with BACC files'
    )
    
    args = parser.parse_args()
    
    # Default is dry-run mode
    dry_run = not args.execute
    base_dir = Path(args.base_dir)
    
    if not base_dir.exists():
        print(f"Error: Base directory '{base_dir}' does not exist!")
        return
    
    # Find all subdirectories
    subdirs = [d for d in base_dir.iterdir() if d.is_dir()]
    
    if not subdirs:
        print(f"No subdirectories found in '{base_dir}'")
        return
    
    print(f"Found {len(subdirs)} subdirectories in '{base_dir}'")
    
    if dry_run:
        print("=" * 70)
        print("DRY RUN MODE - No files will be renamed")
        print("Run with --execute flag to actually rename files")
        print("=" * 70)
    else:
        print("=" * 70)
        print("EXECUTE MODE - Files WILL be renamed!")
        print("=" * 70)
        
        # Ask for confirmation
        response = input("Are you sure you want to proceed? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print("Aborted.")
            return
    
    # Process each subdirectory
    for subdir in sorted(subdirs):
        print(f"\n{'='*70}")
        print(f"Processing directory: {subdir.name}")
        print(f"{'='*70}")
        rename_bacc_files(subdir, dry_run=dry_run)
    
    if dry_run:
        print("\n" + "=" * 70)
        print("To actually rename the files, run with --execute flag:")
        print(f"  python {os.path.basename(__file__)} --execute")
        print("=" * 70)


if __name__ == '__main__':
    main()

