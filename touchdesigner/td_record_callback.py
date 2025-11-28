"""
VirtuCamera Record Callback for TouchDesigner
Provides recording control functions for capturing camera motion data.

Setup:
1. Create a Text DAT with this code
2. Name it 'record_callback'
3. Call functions from buttons or other scripts:
   - op('record_callback').module.start_recording()
   - op('record_callback').module.stop_recording()
   - op('record_callback').module.toggle_recording()
"""


def start_recording():
    """Start recording camera motion."""
    record_state = op('record_state')
    if not record_state:
        print("Error: 'record_state' CHOP not found")
        return False

    # Clear previous recording
    recording = op('recording')
    if recording:
        # Keep only the header row
        while recording.numRows > 1:
            recording.deleteRow(1)

    # Start recording
    record_state.par.value0 = 1
    print("Recording started")
    return True


def stop_recording():
    """Stop recording camera motion."""
    record_state = op('record_state')
    if not record_state:
        print("Error: 'record_state' CHOP not found")
        return False

    record_state.par.value0 = 0

    recording = op('recording')
    frame_count = recording.numRows - 1 if recording else 0
    print(f"Recording stopped ({frame_count} frames)")
    return True


def toggle_recording():
    """Toggle recording on/off."""
    record_state = op('record_state')
    if not record_state:
        print("Error: 'record_state' CHOP not found")
        return False

    if record_state['recording'].eval() == 1:
        return stop_recording()
    else:
        return start_recording()


def is_recording():
    """Check if currently recording."""
    record_state = op('record_state')
    if record_state:
        return record_state['recording'].eval() == 1
    return False


def get_frame_count():
    """Get the number of recorded frames."""
    recording = op('recording')
    if recording:
        return recording.numRows - 1  # Subtract header row
    return 0


def record_frame():
    """
    Manually record a single frame.
    Called automatically by td_parse_callback.py when recording is enabled,
    but can also be called manually for specific frame capture.
    """
    recording = op('recording')
    tracking = op('tracking')

    if not recording or not tracking:
        return False

    frame = absTime.frame
    recording.appendRow([
        frame,
        tracking['tx'].eval(),
        tracking['ty'].eval(),
        tracking['tz'].eval(),
        tracking['rx'].eval(),
        tracking['ry'].eval(),
        tracking['rz'].eval(),
        tracking['fl'].eval()
    ])
    return True
