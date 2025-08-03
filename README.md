# EPD BLE Sender

[Read this document in Chinese (中文说明)](README_zh-CN.md)

A powerful command-line tool to send images and text to various E-Paper Displays (EPD) via Bluetooth Low Energy (BLE).

## ✨ Features

- **Multiple Content Sources**: Supports sending local image files or dynamically generating images from text via the command line.
- **Advanced Text Layout**: 
    - Use a simple markup language to precisely control the **font size**, **alignment** (left/center/right), and **font** for each line of text.
    - Set text color to **black**, **red**, or **white**.
    - Set the image background color to **white**, **black**, or **red**.
- **Device Mode Control**: Switch the display between **Calendar Mode** and **Clock Mode**, or **clear** the screen with simple commands.
- **Smart Device Discovery**: Automatically scans for and connects to specified BLE devices, and can auto-detect screen **resolution** and **MTU size** via device notifications.
- **Rich Image Processing**:
    - **Multiple Dithering Algorithms**: Built-in support for `Floyd-Steinberg`, `Atkinson`, `Jarvis-Stucki`, `Stucki`, and `Bayer` algorithms to optimize image display on monochrome or tri-color screens.
    - **Flexible Resize Modes**: Supports `stretch`, `fit`, and `crop` modes to match the screen dimensions.
- **Powerful Robustness**:
    - **Auto-Reconnect**: Automatically attempts to reconnect if the connection is dropped or a transmission error occurs.
    - **Exponential Backoff**: Uses an exponentially increasing delay between reconnection attempts, significantly improving the success rate in unstable environments.

## ⚙️ Installation and Usage

This project uses [uv](https://github.com/astral-sh/uv) for package management and execution, which provides extremely fast dependency resolution.

1.  **Create a Virtual Environment**
    ```bash
    uv venv
    ```

2.  **Activate the Virtual Environment**
    -   Linux / macOS:
        ```bash
        source .venv/bin/activate
        ```
    -   Windows (PowerShell):
        ```powershell
        .venv\Scripts\Activate.ps1
        ```

3.  **Sync Dependencies**
    ```bash
    uv sync
    ```

## 🚀 How to Use

The `uv run` command ensures that the correct Python interpreter and dependencies are used, even if you forget to activate the virtual environment.

### 1. Scan for Devices

First, scan for nearby BLE devices to find the address of your e-paper display.

```bash
uv run src/main.py scan
```
Take note of your device's address, e.g., `XX:XX:XX:XX:XX:XX`.

### 2. Send Content

Use the `send` command to send an image or text.

**Send an image:**
```bash
uv run src/main.py send --address XX:XX:XX:XX:XX:XX --image /path/to/your/image.png --color-mode bwr --dither floyd
```

**Send text with advanced layout:**
```bash
# This command creates an image with a white background (default)
uv run src/main.py send --address XX:XX:XX:XX:XX:XX \
--text "[size=40,align=center]Weather Report\n[color=red,size=20]High Temp. Alert\n[align=right]2025-08-02" \
--color-mode bwr
```

**Send text with custom background and text colors:**
```bash
# This command creates an image with a black background and white text
uv run src/main.py send --address XX:XX:XX:XX:XX:XX \
--text "[size=30,color=white,align=center]Night Mode" \
--bg-color black
```
**Save the final image locally:**
```bash
# This command processes the image and saves the dithered result to output.png before sending
uv run src/main.py send --address XX:XX:XX:XX:XX:XX \
--image /path/to/your/image.png \
--dither floyd \
--save ./output.png
```


### 3. Switch Display Mode

You can switch the device's built-in display mode between a calendar and a clock.

**Switch to Calendar Mode:**
```bash
uv run src/main.py calendar --address XX:XX:XX:XX:XX:XX
```

**Switch to Clock Mode:**
```bash
uv run src/main.py clock --address XX:XX:XX:XX:XX:XX
```

### 4. Clear the Screen

**Send the clear command:**
```bash
uv run src/main.py clear --address XX:XX:XX:XX:XX:XX
```

## 📚 Command-Line Options Reference

### `scan` command
- `--adapter TEXT`: Specify the Bluetooth adapter to use (e.g., `hci0`).

### `send` command
- `--address TEXT`: **(Required)** The BLE address of the target device.
- `--image TEXT`: Path to the image file to send.
- `--text TEXT`: Text content to render and send. Supports `\n` for newlines.
- `--font TEXT`: Path to the default font file.
- `--size INTEGER`: Default font size.
- `--color TEXT`: Default text color (`black`, `red`, or `white`).
- `--bg-color [white|black|red]`: Set the background color for text rendering (default: `white`).
- `--width INTEGER`: Manually specify the screen width.
- `--height INTEGER`: Manually specify the screen height.
- `--clear`: Clear the screen before sending.
- `--color-mode [bw|bwr]`: Color mode. `bw` for black and white, `bwr` for black, white, and red.
- `--dither [auto|none|floyd|atkinson|jarvis|stucki|bayer]`: Dithering algorithm to use. In 'auto' mode, dithering is enabled for images and disabled for text.
- `--resize-mode [stretch|fit|crop]`: Image resize mode.
- `--interleaved-count INTEGER`: Number of data chunks to send before waiting for a response from the device.
- `--retry INTEGER`: Maximum number of retry attempts on connection failure.
- `--save TEXT`: Save the final processed (dithered) image to the specified path.

### `calendar` command
- `--address TEXT`: **(Required)** The BLE address of the target device.
- `--adapter TEXT`: Specify the Bluetooth adapter to use (e.g., `hci0`).

### `clock` command
- `--address TEXT`: **(Required)** The BLE address of the target device.
- `--adapter TEXT`: Specify the Bluetooth adapter to use (e.g., `hci0`).

### `clear` command
- `--address TEXT`: **(Required)** The BLE address of the target device.
- `--adapter TEXT`: Specify the Bluetooth adapter to use (e.g., `hci0`).

## 📦 Packaging as an Executable

You can use `PyInstaller` to package this tool into a standalone binary, making it easy to run on machines without a Python environment.

1.  **Install PyInstaller**
    ```bash
    uv pip install pyinstaller
    ```

2.  **Run Packaging**

    > **Note**: The `--add-data` argument is crucial for including the default font file in the executable. Please modify the font path according to your system.

    -   **Linux / macOS:**
        ```bash
        pyinstaller --onefile --name epd-sender \
        --add-data="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:." \
        src/main.py
        ```
    -   **Windows:** (Assuming the font is at `C:\Windows\Fonts\arial.ttf`)
        ```powershell
        pyinstaller --onefile --name epd-sender.exe `
        --add-data="C:\Windows\Fonts\arial.ttf;." `
        src/main.py
        ```
    After successful packaging, you will find the `epd-sender` or `epd-sender.exe` file in the `dist` directory.
