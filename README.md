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

The script will **auto-detect the screen resolution** from the device. You can override this with `--width` and `--height`.

### Basic Example

```bash
# Scan for your device's address first
python epd_ble_sender/main.py scan --adapter hci0

# Send an image to a three-color screen
python epd_ble_sender/main.py send --address <YOUR_DEVICE_ADDRESS> --adapter hci0 --image /path/to/image.png --color-mode bwr
```

### Advanced Image Handling

**Resize Modes (`--resize-mode`):**
- `stretch` (default): Stretches the image to fit the screen, ignoring aspect ratio.
- `fit`: Resizes the image to fit within the screen while maintaining aspect ratio, padding with white.
- `crop`: Resizes the image to fill the screen while maintaining aspect ratio, cropping any excess.

```bash
# Crop a large image to fit the screen perfectly
python epd_ble_sender/main.py send --address <ADDR> --adapter hci0 --image /path/to/large.jpg --color-mode bwr --resize-mode crop
```

**Dithering Algorithms (`--dither`):**
- `floyd` (default): Floyd-Steinberg dithering.
- `atkinson`, `jarvis`, `stucki`: Other error-diffusion algorithms.
- `bayer`: Ordered dithering.
- `none`: No dithering.

```bash
# Send an image using Atkinson dithering
python epd_ble_sender/main.py send --address <ADDR> --adapter hci0 --image /path/to/photo.jpg --color-mode bwr --dither atkinson
```

### All Options

*   `--address`: (Required) The BLE address of your EPD.
*   `--adapter`: The Bluetooth adapter to use, e.g., `hci0`.
*   `--image`: Path to the image file.
*   `--text`: Text to display. Use `\n` for new lines.
*   `--font`: Path to a TrueType font file.
*   `--size`: Font size.
*   `--color`: Text color (e.g., `black`, `red`).
*   `--width`, `--height`: (Optional) Override auto-detected screen resolution.
*   `--clear`: A flag to clear the screen before sending new content.
*   `--color-mode`: `bw` for black/white, `bwr` for black/white/red.
*   `--dither`: `none`, `floyd`, `atkinson`, `jarvis`, `stucki`, `bayer`.
*   `--resize-mode`: `stretch`, `fit`, `crop`.
