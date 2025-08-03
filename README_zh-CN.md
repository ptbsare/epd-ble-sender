# EPD BLE Sender - 电子墨水屏蓝牙发送工具

这是一个功能强大的命令行工具，用于通过低功耗蓝牙（BLE）将图像和文本发送到各种电子墨水屏（E-Paper Display, EPD）上。

## ✨ 功能特性

- **多种内容源**: 支持直接发送本地图像文件或通过命令行动态生成文本图像。
- **高级文本排版**: 
    - 使用简单的标记语言，可以精确控制每一行文本的 **字体大小**、**对齐方式**（左/中/右）和 **字体**。
    - 可将文本颜色设置为 **黑**、**红**、**白**。
    - 可将图像背景色设置为 **白**、**黑**、**红**。
- **设备模式控制**: 使用简单命令即可在 **日历模式**、**时钟模式**之间切换，或**清空屏幕**。
- **智能设备发现**: 自动扫描并连接到指定的BLE设备，并能通过设备通知自动检测屏幕 **分辨率** 和 **MTU** 大小。
- **丰富的图像处理**:
    - **多种抖动算法**: 内置 `Floyd-Steinberg`, `Atkinson`, `Jarvis-Stucki`, `Stucki`, 和 `Bayer` 算法，以优化在黑白或三色屏幕上的图像显示效果。
    - **灵活的缩放模式**: 支持 `stretch`（拉伸）、`fit`（适应）和 `crop`（裁剪）模式，以匹配屏幕尺寸。
- **强大的鲁棒性**:
    - **自动重连**: 在遇到连接中断或传输错误时，会自动尝试重新连接。
    - **指数退避**: 重连尝试之间会采用指数级增长的等待时间，大大提高了在不稳定环境下的成功率。

## ⚙️ 安装与运行

本项目使用 [uv](https://github.com/astral-sh/uv) 作为包管理和运行工具，它提供了极快的依赖解析速度。

1.  **创建虚拟环境**
    ```bash
    uv venv
    ```

2.  **激活虚拟环境**
    -   Linux / macOS:
        ```bash
        source .venv/bin/activate
        ```
    -   Windows (PowerShell):
        ```powershell
        .venv\Scripts\Activate.ps1
        ```

3.  **同步依赖**
    ```bash
    uv sync
    ```

## 🚀 使用方法

`uv run` 命令可以确保即使您忘记激活虚拟环境，也能使用正确的Python解释器和依赖。

### 1. 扫描设备

首先，扫描附近的BLE设备以找到你的电子墨水屏的地址。

```bash
uv run src/main.py scan
```
记下你的设备地址，例如 `XX:XX:XX:XX:XX:XX`。

### 2. 发送内容

使用 `send` 命令发送图像或文本。

**发送图像:**
```bash
uv run src/main.py send --address XX:XX:XX:XX:XX:XX --image /path/to/your/image.png --color-mode bwr --dither floyd
```

**使用高级文本排版:**
```bash
# 此命令创建一个白色背景（默认）的图像
uv run src/main.py send --address XX:XX:XX:XX:XX:XX \
--text "[size=40,align=center]天气预报\n[color=red,size=20]高温警告\n[align=right]2025-08-02" \
--color-mode bwr
```

**使用自定义背景和文本颜色:**
```bash
# 此命令创建一个黑色背景和白色文本的图像
uv run src/main.py send --address XX:XX:XX:XX:XX:XX \
--text "[size=30,color=white,align=center]夜间模式" \
--bg-color black
```

### 3. 切换显示模式

你可以切换设备内置的显示模式，在日历和时钟之间选择。

**切换到日历模式:**
```bash
uv run src/main.py calendar --address XX:XX:XX:XX:XX:XX
```

**切换到时钟模式:**
```bash
uv run src/main.py clock --address XX:XX:XX:XX:XX:XX
```

### 4. 清空屏幕

**发送清屏命令:**
```bash
uv run src/main.py clear --address XX:XX:XX:XX:XX:XX
```

## 📚 命令行选项参考

### `scan` 命令
- `--adapter TEXT`: 指定要使用的蓝牙适配器 (例如 `hci0`)。

### `send` 命令
- `--address TEXT`: **(必需)** 目标设备的BLE地址。
- `--image TEXT`: 要发送的图像文件路径。
- `--text TEXT`: 要渲染并发送的文本内容。支持 `\n` 换行。
- `--font TEXT`: 默认字体文件的路径。
- `--size INTEGER`: 默认字体大小。
- `--color TEXT`: 默认文本颜色 (`black`, `red`, 或 `white`)。
- `--bg-color [white|black|red]`: 为文本渲染设置背景颜色 (默认为 `white`)。
- `--width INTEGER`: 手动指定屏幕宽度。
- `--height INTEGER`: 手动指定屏幕高度。
- `--clear`: 发送前清空屏幕。
- `--color-mode [bw|bwr]`: 颜色模式。`bw` 为黑白，`bwr` 为黑白红三色。
- `--dither [auto|none|floyd|atkinson|jarvis|stucki|bayer]`: 使用的抖动算法。'auto' 模式下，为图片启用抖动，为文本禁用抖动。
- `--resize-mode [stretch|fit|crop]`: 图像缩放模式。
- `--interleaved-count INTEGER`: 发送多少个数据块后等待一次设备响应。
- `--retry INTEGER`: 连接失败时的最大重试次数。

### `calendar` 命令
- `--address TEXT`: **(必需)** 目标设备的BLE地址。
- `--adapter TEXT`: 指定要使用的蓝牙适配器 (例如 `hci0`)。

### `clock` 命令
- `--address TEXT`: **(必需)** 目标设备的BLE地址。
- `--adapter TEXT`: 指定要使用的蓝牙适配器 (例如 `hci0`)。

### `clear` 命令
- `--address TEXT`: **(必需)** 目标设备的BLE地址。
- `--adapter TEXT`: 指定要使用的蓝牙适配器 (例如 `hci0`)。

## 📦 打包为可执行文件

你可以使用 `PyInstaller` 将此工具打包成一个独立的二进制文件，方便在没有Python环境的机器上运行。

1.  **安装 PyInstaller**
    ```bash
    uv pip install pyinstaller
    ```

2.  **执行打包**

    > **注意**: `--add-data` 参数对于将默认字体文件包含到可执行文件中至关重要。请根据你的系统修改字体路径。

    -   **Linux / macOS:**
        ```bash
        pyinstaller --onefile --name epd-sender \
        --add-data="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:." \
        src/main.py
        ```
    -   **Windows:** (假设字体在 `C:\Windows\Fonts\arial.ttf`)
        ```powershell
        pyinstaller --onefile --name epd-sender.exe `
        --add-data="C:\Windows\Fonts\arial.ttf;." `
        src/main.py
        ```
    打包成功后，你会在 `dist` 目录下找到 `epd-sender` 或 `epd-sender.exe` 文件。