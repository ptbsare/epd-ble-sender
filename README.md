# EPD BLE Sender

[Read this document in Chinese (中文说明)](README_zh-CN.md)

A powerful command-line tool to send images and text to various E-Paper Displays (EPD) via Bluetooth Low Energy (BLE).

## ✨ Features

- **Multiple Content Sources**: Supports sending local image files or dynamically generating images from text via the command line.
- **Advanced Text Layout**: Use a simple markup language to precisely control the **font size**, **color** (black/red), **alignment** (left/center/right), and **font** for each line of text.
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

**Send text:**
```bash
uv run src/main.py send --address XX:XX:XX:XX:XX:XX --text "Hello World" --size 30
```

**Use advanced text layout:**
```bash
uv run src/main.py send --address XX:XX:XX:XX:XX:XX \
--text "[size=40,align=center]Weather Report\n[color=red,size=20]High Temp. Alert\n[align=right]2025-08-02" \
--color-mode bwr
```

## 📚 Command-Line Options Reference

(For a full list of commands and options, please refer to the [Chinese README](README_zh-CN.md).)

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
