#!/usr/bin/env python3
"""
VirtuCamera Bridge for TouchDesigner
Receives tracking data from VirtuCamera iOS app and forwards to TouchDesigner via UDP.

Usage:
    mamba run -n virtucam python virtucamera_bridge.py

TouchDesigner should listen on UDP port 7000 for JSON messages.
"""

import sys
import os
import math
import time
import json
import socket

# Add the extracted virtucamera module to path
sys.path.insert(0, os.path.dirname(__file__))

from virtucamera import VCBase, VCServer


# Configuration
UDP_HOST = "127.0.0.1"  # TouchDesigner host
UDP_PORT = 7000         # TouchDesigner UDP port
VIRTUCAM_PORT = 23354   # VirtuCamera iOS app port


def matrix_to_euler(matrix):
    """
    Convert a 4x4 transform matrix (as 16-element tuple) to Euler angles (XYZ order).
    Returns angles in degrees.
    """
    rxx, rxy, rxz = matrix[0], matrix[1], matrix[2]
    ryx, ryy, ryz = matrix[4], matrix[5], matrix[6]
    rzx, rzy, rzz = matrix[8], matrix[9], matrix[10]

    if abs(rzx) >= 1.0:
        ry = math.copysign(math.pi / 2, -rzx)
        rz = 0.0
        rx = math.atan2(-ryz, ryy)
    else:
        ry = math.asin(-rzx)
        rx = math.atan2(rzy, rzz)
        rz = math.atan2(ryx, rxx)

    return (math.degrees(rx), math.degrees(ry), math.degrees(rz))


def extract_position(matrix):
    """Extract position (tx, ty, tz) from 4x4 transform matrix."""
    return (matrix[12], matrix[13], matrix[14])


class VirtuCameraBridge(VCBase):
    """Bridge that receives VirtuCamera tracking and sends to TouchDesigner via UDP."""

    def __init__(self, udp_host, udp_port):
        self.udp_host = udp_host
        self.udp_port = udp_port
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        self.focal_length = 35.0
        self.current_transform = (
            1, 0, 0, 0,
            0, 1, 0, 0,
            0, 0, 1, 0,
            0, 0, 0, 1
        )
        self.is_connected = False
        self.last_send_time = 0
        self.send_interval = 0.016  # ~60fps

    def send_to_touchdesigner(self, data):
        """Send JSON data to TouchDesigner via UDP."""
        try:
            message = json.dumps(data)
            self.udp_socket.sendto(message.encode('utf-8'), (self.udp_host, self.udp_port))
        except Exception as e:
            print(f"UDP send error: {e}")

    # SCENE STATE RELATED METHODS

    def get_playback_state(self, vcserver):
        return (0, 0, 100)

    def get_playback_fps(self, vcserver):
        return 30.0

    def set_frame(self, vcserver, frame):
        pass

    def set_playback_range(self, vcserver, start, end):
        pass

    def start_playback(self, vcserver, forward):
        pass

    def stop_playback(self, vcserver):
        pass

    # CAMERA RELATED METHODS

    def get_scene_cameras(self, vcserver):
        return ["VirtualCamera"]

    def get_camera_exists(self, vcserver, camera_name):
        return True

    def get_camera_has_keys(self, vcserver, camera_name):
        return (False, False)

    def get_camera_focal_length(self, vcserver, camera_name):
        return self.focal_length

    def get_camera_transform(self, vcserver, camera_name):
        return self.current_transform

    def set_camera_focal_length(self, vcserver, camera_name, focal_length):
        self.focal_length = focal_length

    def set_camera_transform(self, vcserver, camera_name, transform_matrix):
        """Called when new transform data arrives from the iOS app."""
        self.current_transform = transform_matrix

        # Rate limit sending
        current_time = time.time()
        if current_time - self.last_send_time < self.send_interval:
            return
        self.last_send_time = current_time

        # Extract position and rotation
        pos = extract_position(transform_matrix)
        rot = matrix_to_euler(transform_matrix)

        # Send to TouchDesigner
        data = {
            "px": round(pos[0], 4),
            "py": round(pos[1], 4),
            "pz": round(pos[2], 4),
            "rx": round(rot[0], 4),
            "ry": round(rot[1], 4),
            "rz": round(rot[2], 4),
            "fl": round(self.focal_length, 2),
            "connected": self.is_connected
        }
        self.send_to_touchdesigner(data)

        # Also print to terminal for debugging
        print(f"\rPos: X={pos[0]:>8.3f} Y={pos[1]:>8.3f} Z={pos[2]:>8.3f} | "
              f"Rot: X={rot[0]:>7.2f} Y={rot[1]:>7.2f} Z={rot[2]:>7.2f} | "
              f"FL: {self.focal_length:>5.1f}mm", end="")
        sys.stdout.flush()

    def set_camera_flen_keys(self, vcserver, camera_name, keyframes, focal_length_values):
        pass

    def set_camera_transform_keys(self, vcserver, camera_name, keyframes, transform_matrix_values):
        pass

    def remove_camera_keys(self, vcserver, camera_name):
        pass

    def create_new_camera(self, vcserver):
        return "VirtualCamera"

    # VIEWPORT CAPTURE RELATED METHODS

    def capture_will_start(self, vcserver):
        vcserver.set_capture_resolution(1, 1)
        vcserver.set_capture_mode(vcserver.CAPMODE_SCREENSHOT, vcserver.CAPFORMAT_UBYTE_RGBA)

    def look_through_camera(self, vcserver, camera_name):
        pass

    # APP/SERVER FEEDBACK METHODS

    def client_connected(self, vcserver, client_ip, client_port):
        self.is_connected = True
        print(f"\n[CONNECTED] Client connected from {client_ip}:{client_port}")
        print("Sending tracking data to TouchDesigner...\n")
        sys.stdout.flush()

        # Send connection status
        self.send_to_touchdesigner({"connected": True, "event": "connected"})

    def client_disconnected(self, vcserver):
        self.is_connected = False
        print("\n\n[DISCONNECTED] Client disconnected")
        sys.stdout.flush()

        # Send disconnection status
        self.send_to_touchdesigner({"connected": False, "event": "disconnected"})


def main():
    print("=" * 60)
    print("VirtuCamera Bridge for TouchDesigner")
    print("=" * 60)
    print(f"UDP Target: {UDP_HOST}:{UDP_PORT}")
    print(f"VirtuCamera Port: {VIRTUCAM_PORT}")

    # Create the bridge instance
    bridge = VirtuCameraBridge(UDP_HOST, UDP_PORT)

    # Create server
    server = VCServer(
        platform="TD-Bridge",  # Max 10 chars
        plugin_version=(1, 0, 0),
        event_mode=VCServer.EVENTMODE_PULL,
        vcbase=bridge
    )

    # Start serving
    print(f"\nStarting server on port {VIRTUCAM_PORT}...")
    server.start_serving(VIRTUCAM_PORT)

    if not server.is_serving:
        print("ERROR: Failed to start server!")
        print("Port may be in use. Try: lsof -ti:23354 | xargs kill -9")
        return 1

    print(f"Server started successfully!")
    print(f"\nScan the QR code in the VirtuCamera app to connect.")
    print(f"(QR code saved to virtucamera_qr.png)")
    print(f"\nPress Ctrl+C to stop.\n")

    # Save QR code image
    qr_path = os.path.join(os.path.dirname(__file__), "virtucamera_qr.png")
    server.write_qr_image_png(qr_path, 3)

    # Add diagnostic info
    print(f"\nServer IP addresses detected:")
    try:
        from virtucamera.third_party import ifaddr
        adapters = ifaddr.get_adapters()
        for adapter in adapters:
            for ip in adapter.ips:
                if isinstance(ip.ip, str) and not ip.ip.startswith('127.'):
                    print(f"  - {ip.ip} ({adapter.nice_name})")
    except Exception as e:
        print(f"  Could not detect IPs: {e}")

    print(f"\nIf connection fails, ensure your iPhone can reach one of these IPs on port {VIRTUCAM_PORT}")

    # Main event loop
    try:
        while server.is_serving:
            server.execute_pending_events()
            time.sleep(0.001)
    except KeyboardInterrupt:
        print("\n\nShutting down...")
    finally:
        server.stop_serving()
        bridge.udp_socket.close()
        print("Server stopped.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
