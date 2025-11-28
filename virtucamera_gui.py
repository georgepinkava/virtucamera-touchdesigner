#!/usr/bin/env python3
"""
VirtuCamera GUI
PyQt5 application that displays tracking data from VirtuCamera iOS app.
"""

import sys
import os
import math
import time
import json
import socket

# Add the extracted virtucamera module to path
sys.path.insert(0, os.path.dirname(__file__))

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QGroupBox, QGridLayout)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont, QPalette, QColor, QPixmap

from virtucamera import VCBase, VCServer


# UDP Configuration for TouchDesigner
UDP_HOST = "127.0.0.1"
UDP_PORT = 7000


def matrix_to_euler(matrix):
    """Convert a 4x4 transform matrix to Euler angles (XYZ order) in degrees."""
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


class VirtuCameraGUI(VCBase):
    """VirtuCamera plugin that updates GUI with tracking data and forwards to TouchDesigner."""

    def __init__(self, main_window):
        self.main_window = main_window
        self.focal_length = 35.0
        self.current_transform = (
            1, 0, 0, 0,
            0, 1, 0, 0,
            0, 0, 1, 0,
            0, 0, 0, 1
        )

        # UDP socket for TouchDesigner bridge
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_host = UDP_HOST
        self.udp_port = UDP_PORT
        self.is_connected = False

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
        self.main_window.update_focal_length(focal_length)

    def set_camera_transform(self, vcserver, camera_name, transform_matrix):
        """Called when new transform data arrives from the iOS app."""
        self.current_transform = transform_matrix
        pos = extract_position(transform_matrix)
        rot = matrix_to_euler(transform_matrix)
        self.main_window.update_transform(pos, rot)

        # Send to TouchDesigner via UDP
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
        self.main_window.set_connected(True, f"{client_ip}:{client_port}")
        self.send_to_touchdesigner({"connected": True, "event": "connected"})

    def client_disconnected(self, vcserver):
        self.is_connected = False
        self.main_window.set_connected(False)
        self.send_to_touchdesigner({"connected": False, "event": "disconnected"})


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VirtuCamera GUI")
        self.setMinimumSize(500, 400)

        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Left side - QR Code
        qr_group = QGroupBox("Scan with VirtuCamera App")
        qr_layout = QVBoxLayout(qr_group)
        self.qr_label = QLabel()
        self.qr_label.setAlignment(Qt.AlignCenter)
        self.qr_label.setMinimumSize(200, 200)
        qr_layout.addWidget(self.qr_label)
        main_layout.addWidget(qr_group)

        # Right side - Data display
        right_widget = QWidget()
        layout = QVBoxLayout(right_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(right_widget)

        # Status section
        status_group = QGroupBox("Connection Status")
        status_layout = QHBoxLayout(status_group)
        self.status_label = QLabel("Waiting for connection...")
        self.status_label.setFont(QFont("Arial", 12, QFont.Bold))
        status_layout.addWidget(self.status_label)
        layout.addWidget(status_group)

        # Position section
        pos_group = QGroupBox("Position")
        pos_layout = QGridLayout(pos_group)

        self.pos_labels = {}
        for i, axis in enumerate(['X', 'Y', 'Z']):
            label = QLabel(f"{axis}:")
            label.setFont(QFont("Arial", 11))
            pos_layout.addWidget(label, 0, i*2)

            value = QLabel("0.000")
            value.setFont(QFont("Consolas", 14, QFont.Bold))
            value.setMinimumWidth(100)
            value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            pos_layout.addWidget(value, 0, i*2+1)
            self.pos_labels[axis] = value

        layout.addWidget(pos_group)

        # Rotation section
        rot_group = QGroupBox("Rotation (degrees)")
        rot_layout = QGridLayout(rot_group)

        self.rot_labels = {}
        for i, axis in enumerate(['X', 'Y', 'Z']):
            label = QLabel(f"{axis}:")
            label.setFont(QFont("Arial", 11))
            rot_layout.addWidget(label, 0, i*2)

            value = QLabel("0.00")
            value.setFont(QFont("Consolas", 14, QFont.Bold))
            value.setMinimumWidth(100)
            value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            rot_layout.addWidget(value, 0, i*2+1)
            self.rot_labels[axis] = value

        layout.addWidget(rot_group)

        # Focal length section
        fl_group = QGroupBox("Focal Length")
        fl_layout = QHBoxLayout(fl_group)
        self.fl_label = QLabel("35.0 mm")
        self.fl_label.setFont(QFont("Consolas", 16, QFont.Bold))
        fl_layout.addWidget(self.fl_label)
        layout.addWidget(fl_group)

        # Server info section
        info_group = QGroupBox("Server Info")
        info_layout = QVBoxLayout(info_group)
        self.server_info = QLabel("Initializing...")
        self.server_info.setFont(QFont("Arial", 10))
        self.server_info.setWordWrap(True)
        info_layout.addWidget(self.server_info)
        layout.addWidget(info_group)

        # Add stretch to push everything up
        layout.addStretch()

        # Initialize server
        self.vc_plugin = VirtuCameraGUI(self)
        self.server = VCServer(
            platform="GUI",
            plugin_version=(1, 0, 0),
            event_mode=VCServer.EVENTMODE_PULL,
            vcbase=self.vc_plugin
        )

        # Start server
        port = 23354
        self.server.start_serving(port)

        if self.server.is_serving:
            # Save QR code
            qr_path = os.path.join(os.path.dirname(__file__), "virtucamera_qr.png")
            self.server.write_qr_image_png(qr_path, 3)

            # Load and display QR code
            pixmap = QPixmap(qr_path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.qr_label.setPixmap(scaled)

            # Get IP addresses
            ip_info = self._get_ip_addresses()
            self.server_info.setText(
                f"Server running on port {port}\n"
                f"TouchDesigner UDP: {UDP_HOST}:{UDP_PORT}\n"
                f"QR Code saved to: virtucamera_qr.png\n\n"
                f"IP Addresses:\n{ip_info}"
            )
        else:
            self.server_info.setText("ERROR: Failed to start server!")
            self.status_label.setText("Server failed to start")
            self.status_label.setStyleSheet("color: red;")

        # Timer for processing events
        self.timer = QTimer()
        self.timer.timeout.connect(self.process_events)
        self.timer.start(1)  # 1ms interval

        # Update counter for debugging
        self.event_count = 0

    def _get_ip_addresses(self):
        """Get list of IP addresses."""
        try:
            from virtucamera.third_party import ifaddr
            adapters = ifaddr.get_adapters()
            ips = []
            for adapter in adapters:
                for ip in adapter.ips:
                    if isinstance(ip.ip, str) and not ip.ip.startswith('127.'):
                        ips.append(f"  {ip.ip} ({adapter.nice_name})")
            return "\n".join(ips) if ips else "No network interfaces found"
        except Exception as e:
            return f"Could not detect IPs: {e}"

    def process_events(self):
        """Process VirtuCamera server events."""
        if self.server.is_serving:
            self.server.execute_pending_events()
            self.event_count += 1

    def update_transform(self, pos, rot):
        """Update position and rotation display."""
        self.pos_labels['X'].setText(f"{pos[0]:.3f}")
        self.pos_labels['Y'].setText(f"{pos[1]:.3f}")
        self.pos_labels['Z'].setText(f"{pos[2]:.3f}")

        self.rot_labels['X'].setText(f"{rot[0]:.2f}")
        self.rot_labels['Y'].setText(f"{rot[1]:.2f}")
        self.rot_labels['Z'].setText(f"{rot[2]:.2f}")

    def update_focal_length(self, fl):
        """Update focal length display."""
        self.fl_label.setText(f"{fl:.1f} mm")

    def set_connected(self, connected, client_info=""):
        """Update connection status."""
        if connected:
            self.status_label.setText(f"Connected: {client_info}")
            self.status_label.setStyleSheet("color: green;")
        else:
            self.status_label.setText("Disconnected")
            self.status_label.setStyleSheet("color: red;")

    def closeEvent(self, event):
        """Clean up on window close."""
        self.timer.stop()
        if self.server.is_serving:
            self.server.stop_serving()
        self.vc_plugin.udp_socket.close()
        event.accept()


def main():
    app = QApplication(sys.argv)

    # Set dark theme
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ToolTipBase, Qt.white)
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(palette)

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
