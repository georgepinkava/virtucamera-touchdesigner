"""
VirtuCamera Parse Callback for TouchDesigner
Paste this code into a DAT Execute DAT watching the UDP In DAT.

Setup:
1. Create a DAT Execute DAT
2. Set 'DAT' parameter to your UDP In DAT (e.g., 'udp_in')
3. Enable 'Table Change' callback
4. Paste this code into the DAT Execute
"""

import json

def onTableChange(dat, changes, modifier):
    """Called when the UDP In DAT receives new data."""

    # Get the latest row (most recent message)
    if dat.numRows < 1:
        return

    # Get the raw message (last row, first column)
    try:
        raw_message = dat[dat.numRows - 1, 0].val
    except:
        return

    # Parse JSON
    try:
        data = json.loads(raw_message)
    except json.JSONDecodeError:
        print(f"Invalid JSON: {raw_message}")
        return

    # Update tracking CHOP
    tracking = op('tracking')
    if tracking:
        if 'px' in data:
            tracking.par.value0 = data['px']  # tx
        if 'py' in data:
            tracking.par.value1 = data['py']  # ty
        if 'pz' in data:
            tracking.par.value2 = data['pz']  # tz
        if 'rx' in data:
            tracking.par.value3 = data['rx']  # rx
        if 'ry' in data:
            tracking.par.value4 = data['ry']  # ry
        if 'rz' in data:
            tracking.par.value5 = data['rz']  # rz
        if 'fl' in data:
            tracking.par.value6 = data['fl']  # focal length

    # Handle connection events
    if 'event' in data:
        if data['event'] == 'connected':
            print("VirtuCamera connected!")
            # Update connection status indicator if you have one
            status = op('connection_status')
            if status:
                status.par.value0 = 1
        elif data['event'] == 'disconnected':
            print("VirtuCamera disconnected!")
            status = op('connection_status')
            if status:
                status.par.value0 = 0

    # Recording (if enabled)
    record_state = op('record_state')
    if record_state and record_state['recording'].eval() == 1:
        recording_table = op('recording')
        if recording_table and 'px' in data:
            frame = absTime.frame
            recording_table.appendRow([
                frame,
                data.get('px', 0),
                data.get('py', 0),
                data.get('pz', 0),
                data.get('rx', 0),
                data.get('ry', 0),
                data.get('rz', 0),
                data.get('fl', 35)
            ])

# Legacy callbacks (for older TD versions)
def onRowChange(dat, rows, modifier):
    pass

def onColChange(dat, cols, modifier):
    pass

def onCellChange(dat, cells, modifier):
    pass

def onSizeChange(dat, modifier):
    pass
