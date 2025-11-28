"""
VirtuCamera CSV Export for TouchDesigner
Use this script to export recorded camera motion to CSV.

Setup:
1. Create a Text DAT with this code
2. Create a Button COMP for export
3. In the Button's panel execute, call: op('export_script').run()

Or run manually from the textport:
    op('export_script').run()
"""

import os
from datetime import datetime

def export_recording_to_csv():
    """Export the recording table to a CSV file."""

    recording = op('recording')
    if not recording:
        print("Error: 'recording' table not found")
        return

    if recording.numRows <= 1:  # Only header row
        print("No recording data to export")
        return

    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"virtucamera_recording_{timestamp}.csv"

    # Get export directory (use project folder or specify path)
    export_dir = project.folder
    if not export_dir:
        export_dir = os.path.expanduser("~/Documents")

    filepath = os.path.join(export_dir, filename)

    # Write CSV
    try:
        with open(filepath, 'w') as f:
            for row in range(recording.numRows):
                row_data = [recording[row, col].val for col in range(recording.numCols)]
                f.write(','.join(str(v) for v in row_data) + '\n')

        print(f"Exported {recording.numRows - 1} frames to: {filepath}")
        return filepath

    except Exception as e:
        print(f"Export error: {e}")
        return None


def clear_recording():
    """Clear the recording table (keep header)."""
    recording = op('recording')
    if recording:
        # Keep only the header row
        while recording.numRows > 1:
            recording.deleteRow(1)
        print("Recording cleared")


def start_recording():
    """Start recording camera motion."""
    record_state = op('record_state')
    if record_state:
        record_state.par.value0 = 1
        print("Recording started")

        # Clear previous recording
        clear_recording()


def stop_recording():
    """Stop recording camera motion."""
    record_state = op('record_state')
    if record_state:
        record_state.par.value0 = 0

        recording = op('recording')
        frame_count = recording.numRows - 1 if recording else 0
        print(f"Recording stopped ({frame_count} frames)")


# Main entry point when script is run
if __name__ != '__main__':
    # This runs when called from TouchDesigner
    export_recording_to_csv()
