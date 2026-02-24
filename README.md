# ONVIF Network Camera Scanner

This project is a Python-based CLI tool designed to automatically discover ONVIF-compatible cameras across local networks (LAN) and VPN connections, inspect their capabilities, and provide structured results in a console table and JSON format.

## Features

- **WS-Discovery**: Uses multicast (UDP) to discover ONVIF devices on the local network.
- **IP Range Scanning**: Scans user-defined CIDR ranges (e.g., `10.8.0.0/24`) to find cameras, suitable for VPN environments where multicast is often blocked.
- **Camera Inspection**: Connects to discovered cameras to retrieve:
    - Manufacturer, Model, Firmware, Serial Number.
    - Media Profiles (RTSP Stream URIs).
    - PTZ Support and Status (Pan, Tilt, Zoom positions and limits).
- **Structured Output**: Prints a formatted table to the console and exports detailed data to `cameras.json`.

## Installation

1.  Clone the repository.
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

Run the scanner using the CLI entry point:

```bash
python3 -m onvif_scanner.cli --user admin --password password123
```

### Options

- `--mode {ws-discovery,ip-range}`: Discovery mode (default: `ws-discovery`).
- `--subnet SUBNET`: CIDR subnet for IP range scanning (required for `ip-range` mode).
- `--user USER`: Camera username (required).
- `--password PASSWORD`: Camera password (required).
- `--output OUTPUT`: Output JSON file path (default: `cameras.json`).
- `--verbose`: Enable verbose logging.

### Examples

**Scan Local Network (WS-Discovery):**
```bash
python3 -m onvif_scanner.cli --user admin --password secret
```

**Scan VPN Subnet (IP Range):**
```bash
python3 -m onvif_scanner.cli --mode ip-range --subnet 10.8.0.0/24 --user admin --password secret
```

## File Descriptions

The project is organized as a Python package `onvif_scanner`.

- **`onvif_scanner/__init__.py`**:
  Initializes the `onvif_scanner` package.

- **`onvif_scanner/cli.py`**:
  The main entry point for the command-line interface. It uses `argparse` to handle user arguments, orchestrates the scanning process using `WSDiscoveryScanner` or `IPRangeScanner`, initiates inspection with `CameraInspector`, and calls the output functions.

- **`onvif_scanner/scanner.py`**:
  Contains the discovery logic.
  - `WSDiscoveryScanner`: Implements a custom UDP multicast probe to find ONVIF devices compliant with WS-Discovery.
  - `IPRangeScanner`: Implements a multi-threaded scanner that checks IP addresses in a CIDR block for ONVIF service endpoints on ports 80 and 8080.

- **`onvif_scanner/inspector.py`**:
  Handles the interaction with individual cameras using the `onvif-zeep` library.
  - `CameraInspector`: Connects to a camera and retrieves device information (model, firmware), media profiles (RTSP URIs), and PTZ status.

- **`onvif_scanner/models.py`**:
  Defines the data structures used throughout the application.
  - `CameraInfo`: Main container for camera data.
  - `StreamProfile`: Represents a media profile and its RTSP URI.
  - `PTZInfo`: Container for PTZ capabilities, status, and limits.

- **`onvif_scanner/output.py`**:
  Handles the presentation of results.
  - `print_summary_table`: Uses the `rich` library to display a formatted table of discovered cameras.
  - `export_to_json`: Serializes the `CameraInfo` objects to a JSON file.

- **`onvif_scanner/utils.py`**:
  Contains utility functions, specifically `get_network_interfaces`, which attempts to list local IP addresses to bind the multicast discovery socket to specific interfaces.

- **`tests/test_scanner.py`**:
  Unit tests for the discovery modules (`WSDiscoveryScanner`, `IPRangeScanner`), mocking network sockets and requests.

- **`tests/test_inspector.py`**:
  Unit tests for the `CameraInspector`, mocking the `onvif-zeep` camera and service objects.
