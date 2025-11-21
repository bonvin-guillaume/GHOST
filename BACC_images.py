"""
Script to extract frames from BACC AVI files based on GHOST event dates.

This script:
1. Reads event data from ghost_df.csv
2. Searches for corresponding AVI files in the BACC-LYR network path based on date
3. Extracts frames (1 fps) from all AVI files found for each date
"""

import pandas as pd
import os
from datetime import datetime
from pathlib import Path
import subprocess

# Configuration
BASE_PATH = r"\\birkeland.unis.no\KHO\BACC\BACC-LYR"
CSV_FILE = "ghost_df.csv"
OUTPUT_DIR = "BACC_frames"  # Base directory for extracted frames
FFMPEG_PATH = r"C:\Users\guillaumeb\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0-full_build\bin\ffmpeg.exe"


def get_bacc_folder_path(date_str):
    """
    Construct the BACC folder path from a date string.
    
    Args:
        date_str: Date in format YYYY-MM-DD
    
    Returns:
        Path to BACC folder, e.g., \\birkeland.unis.no\KHO\BACC\BACC-LYR\2022\December\01122022
    """
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        year = date_obj.strftime('%Y')
        month = date_obj.strftime('%B')  # Full month name (e.g., December)
        day_folder = date_obj.strftime('%d%m%Y')  # Format: DDMMYYYY
        
        folder_path = os.path.join(BASE_PATH, year, month, day_folder)
        return folder_path
    except ValueError:
        return None


def extract_frames_from_avi(avi_path, output_dir, event_date):
    """
    Extract frames from AVI file using ffmpeg at 1 fps.
    
    Args:
        avi_path: Full path to the AVI file
        output_dir: Directory to save extracted frames
        event_date: Date string for organizing output
    
    Returns:
        True if successful, False otherwise
    """
    avi_filename = os.path.basename(avi_path)
    avi_name_without_ext = os.path.splitext(avi_filename)[0]
    
    # Create output directory for this date
    frames_output_dir = os.path.join(output_dir, event_date)
    os.makedirs(frames_output_dir, exist_ok=True)
    
    # Output pattern for frames
    output_pattern = os.path.join(frames_output_dir, f"BACC_LYR_{avi_name_without_ext}_%04d.png")
    
    # FFmpeg command to extract frames at 1 fps
    ffmpeg_cmd = [
        FFMPEG_PATH,
        '-i', avi_path,
        '-vf', 'fps=1',
        '-y',  # Overwrite output files without asking
        output_pattern
    ]
    
    try:
        print(f"  Extracting frames from {avi_filename}...")
        result = subprocess.run(
            ffmpeg_cmd,
            capture_output=True,
            text=True,
            check=True
        )
        print(f"  ✓ Frames extracted to {frames_output_dir}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ✗ Error extracting frames from {avi_filename}: {e}")
        print(f"    stderr: {e.stderr}")
        return False
    except FileNotFoundError:
        print(f"  ✗ ffmpeg not found at: {FFMPEG_PATH}")
        print(f"    Please check the FFMPEG_PATH configuration in the script.")
        return False


def process_events():
    """Main function to process all events from the CSV file."""
    
    # Check if ffmpeg exists
    if not os.path.exists(FFMPEG_PATH):
        print(f"Error: ffmpeg not found at {FFMPEG_PATH}")
        print(f"Please check the FFMPEG_PATH configuration in the script.")
        return
    
    # Check if CSV file exists
    if not os.path.exists(CSV_FILE):
        print(f"Error: {CSV_FILE} not found!")
        return
    
    # Read CSV file
    print(f"Reading {CSV_FILE}...")
    df = pd.read_csv(CSV_FILE)
    
    # Get unique dates (drop NaN values)
    unique_dates = df['Date'].dropna().unique()
    
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Statistics
    total_events = len(df)
    total_unique_dates = len(unique_dates)
    processed_dates = 0
    skipped_dates = 0
    total_avis_processed = 0
    
    print(f"\nFound {total_events} events with {total_unique_dates} unique dates to process...\n")
    
    # Process each unique date
    for idx, date_str in enumerate(sorted(unique_dates)):
        
        print(f"Date {idx + 1}/{total_unique_dates}: {date_str}")
        
        # Count how many events have this date
        event_count = len(df[df['Date'] == date_str])
        if event_count > 1:
            print(f"  ℹ This date appears in {event_count} events")
        
        # Get BACC folder path
        bacc_folder = get_bacc_folder_path(date_str)
        if bacc_folder is None:
            print("  ⊘ Skipped: Invalid date format")
            skipped_dates += 1
            continue
        
        # Check if folder exists
        if not os.path.exists(bacc_folder):
            print(f"  ⊘ Folder not found: {bacc_folder}")
            skipped_dates += 1
            continue
        
        print(f"  ✓ Folder found: {bacc_folder}")
        
        # List AVI files in the folder
        try:
            avi_files = [f for f in os.listdir(bacc_folder) if f.lower().endswith('.avi')]
        except Exception as e:
            print(f"  ✗ Error listing files: {e}")
            skipped_dates += 1
            continue
        
        if not avi_files:
            print("  ⊘ No AVI files found in folder")
            skipped_dates += 1
            continue
        
        print(f"  ✓ Found {len(avi_files)} AVI file(s) to process")
        
        # Process all AVI files
        for avi_file in sorted(avi_files):
            avi_path = os.path.join(bacc_folder, avi_file)
            success = extract_frames_from_avi(avi_path, OUTPUT_DIR, date_str)
            if success:
                total_avis_processed += 1
        
        processed_dates += 1
        print()
    
    # Print summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total events in CSV: {total_events}")
    print(f"Unique dates: {total_unique_dates}")
    print(f"Processed dates: {processed_dates}")
    print(f"Skipped dates: {skipped_dates}")
    print(f"Total AVI files processed: {total_avis_processed}")
    print(f"Frames saved to: {os.path.abspath(OUTPUT_DIR)}")
    print("=" * 60)


if __name__ == "__main__":
    print("=" * 60)
    print("BACC AVI Frame Extraction Script")
    print("=" * 60)
    print(f"Using ffmpeg: {FFMPEG_PATH}")
    print("=" * 60)
    process_events()

