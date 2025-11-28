# VirtuCamera TouchDesigner Integration

Receive camera tracking data from the [VirtuCamera iOS app](https://apps.apple.com/app/virtucamera/id6446124523) in TouchDesigner.

## Architecture

```
VirtuCamera iOS App
        │
        │ TCP:23354
        ▼
virtucamera_bridge.py (Python 3.10)
        │
        │ UDP:7000 (JSON)
        ▼
TouchDesigner
```

## Prerequisites

1. VirtuCamera iOS app installed on your device
2. TouchDesigner installed
3. Python 3.10+ with the virtucamera module (included in this repo)

## Quick Start

### 1. Start the Bridge

```bash
python virtucamera_bridge.py
```

A QR code will be generated at `virtucamera_qr.png`. Scan it with the VirtuCamera app.

### 2. Set Up TouchDesigner

Follow the setup instructions below to create the network.

---

## TouchDesigner Network Setup

### Step 1: Create UDP Input

1. Add a **UDP In DAT**
   - Name: `udp_in`
   - Network Port: `7000`
   - Row/Callback Format: `One Per Message`
   - Active: `On`

### Step 2: Create Tracking Channels

1. Add a **Constant CHOP**
   - Name: `tracking`
   - Add 7 channels: `tx ty tz rx ry rz fl`
   - Default values: `0 0 0 0 0 0 35`

### Step 3: Create Parse Script

1. Add a **DAT Execute DAT**
   - Name: `parse_exec`
   - DAT: `udp_in`
   - Table Change: `On`
   - Paste the code from `touchdesigner/td_parse_callback.py` into the DAT

### Step 4: Create Camera

1. Add a **Camera COMP**
   - Name: `virtucamera`

2. Set the camera transform parameters to reference the tracking CHOP:
   - Translate X: `op('tracking')['tx']`
   - Translate Y: `op('tracking')['ty']`
   - Translate Z: `op('tracking')['tz']`
   - Rotate X: `op('tracking')['rx']`
   - Rotate Y: `op('tracking')['ry']`
   - Rotate Z: `op('tracking')['rz']`

3. For focal length (optional):
   - Add a **Lens COMP** or use expressions on Camera's FOV parameter

### Step 5: Create Recording System

1. Add a **Table DAT**
   - Name: `recording`
   - First row: `frame,px,py,pz,rx,ry,rz,fl`

2. Add a **Constant CHOP** for recording state
   - Name: `record_state`
   - Channel: `recording` (0=off, 1=on)

3. Add buttons for record/export (use Button COMP or Panel)

### Step 6: Create 3D Scene

1. Add a **Geometry COMP** with your scene
2. Add a **Render TOP**
   - Camera: `virtucamera`
3. Add an **Out TOP** to view the result

---

## File Reference

| File | Description |
|------|-------------|
| `virtucamera_bridge.py` | Bridge server that receives iOS app data and forwards to TD |
| `touchdesigner/td_parse_callback.py` | Python code for DAT Execute to parse JSON |
| `touchdesigner/td_record_callback.py` | Python code for recording control |
| `touchdesigner/td_export_csv.py` | Python code for CSV export |
| `virtucamera/` | VirtuCamera Python module (required by bridge) |

---

## Troubleshooting

### No data in TouchDesigner
- Check that the bridge is running
- Verify UDP port 7000 is not blocked by firewall
- Check `udp_in` DAT is Active

### Camera not moving
- Verify expressions are correct on Camera COMP
- Check that `tracking` CHOP channels are updating

### High latency
- Reduce network congestion
- The bridge sends at ~60fps by default

### Connection issues
- Ensure your iPhone and computer are on the same network
- Check the QR code contains a reachable IP address
- Try manually entering the IP:port in the VirtuCamera app

---

## License

See the VirtuCamera app terms for usage rights.
