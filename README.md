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
    This will create a `.venv` directory and install the required packages.

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

### Send an Image

For a standard black and white screen:
```bash
python epd_ble_sender/main.py send --address <YOUR_DEVICE_ADDRESS> --adapter hci0 --image /path/to/your/image.png
```

For a **black/white/red** three-color screen, use the `--color-mode bwr` option:
```bash
python epd_ble_sender/main.py send --address <YOUR_DEVICE_ADDRESS> --adapter hci0 --image /path/to/your/image.png --color-mode bwr
```

### Send Text

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
*   `--width`: The width of the EPD screen in pixels.
*   `--height`: The height of the EPD screen in pixels.
*   `--clear`: A flag to clear the screen before sending new content.
*   `--color-mode`: `bw` for black/white, `bwr` for black/white/red.
