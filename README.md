# EPD BLE Sender

A command-line tool to send images and text to an E-Paper Display (EPD) via Bluetooth Low Energy (BLE).

## Installation

This project uses a `requirements.txt` file and can be run with `uv`.

1.  **Install uv:**
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

2.  **Create a virtual environment and install dependencies:**
    Navigate to the `pyproject` directory and run:
    ```bash
    uv venv
    uv pip sync -r requirements.txt
    ```
    This will create a `.venv` directory and install the required packages, including `numpy`.

## Usage

Activate the virtual environment first:
```bash
source .venv/bin/activate
```

The tool provides two main commands: `scan` and `send`.

### Scan for Devices

To find the address of your EPD, run the `scan` command. Use `--adapter` if you have multiple Bluetooth adapters.
```bash
python epd_ble_sender/main.py scan --adapter hci0
```

### Send an Image or Text

The script will now **auto-detect the screen resolution** from the device upon connection. You no longer need to specify `--width` and `--height` unless you want to override the detected values.

**Example for a three-color screen (e.g., 4.2-inch):**
```bash
python epd_ble_sender/main.py send --address <YOUR_DEVICE_ADDRESS> --adapter hci0 --image /path/to/your/image.png --color-mode bwr
```

**Example sending red text:**
```bash
python epd_ble_sender/main.py send --address <YOUR_DEVICE_ADDRESS> --adapter hci0 --text "Hello World\nIn Red" --color red --color-mode bwr
```

### All Options

*   `--address`: (Required) The BLE address of your EPD.
*   `--adapter`: The Bluetooth adapter to use, e.g., `hci0`. Highly recommended.
*   `--image`: Path to the image file.
*   `--text`: Text to display. Use `\n` for new lines.
*   `--font`: Path to a TrueType font file.
*   `--size`: Font size.
*   `--color`: Text color (e.g., `black`, `red`).
*   `--width`, `--height`: (Optional) Override auto-detected screen resolution.
*   `--clear`: A flag to clear the screen before sending new content.
*   `--color-mode`: `bw` for black/white, `bwr` for black/white/red.
*   `--dither`: Dithering algorithm to use. `floyd` (default) or `none`.
