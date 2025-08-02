import asyncio
import click
from bleak import BleakClient, BleakScanner
from PIL import Image, ImageDraw, ImageFont
import logging
import sys
import numpy as np

# Constants
SERVICE_UUID = "62750001-d828-918d-fb46-b6c11c675aec"
CHARACTERISTIC_UUID = "62750002-d828-918d-fb46-b6c11c675aec"

# Based on canvasSizes array and common e-paper drivers
# This is a crucial mapping that was missing.
DRIVER_TO_RESOLUTION = {
    # Guessed values based on common drivers and main.js list
    0x00: (296, 128), # 2.9"
    0x01: (250, 122), # 2.13"
    0x02: (400, 300), # 4.2" b/w
    0x03: (400, 300), # 4.2" b/w/r
    0x04: (800, 480), # 7.5" b/w/r
    # Add other mappings as needed
}

# Palettes
THREE_COLOR_PALETTE = np.array([[0, 0, 0], [255, 255, 255], [255, 0, 0]])
TWO_COLOR_PALETTE = np.array([[0, 0, 0], [255, 255, 255]])

class EpdCmd:
    INIT = 0x01
    CLEAR = 0x02
    REFRESH = 0x05
    WRITE_IMG = 0x30

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', stream=sys.stdout)
logger = logging.getLogger(__name__)

def floyd_steinberg_dither(image: Image.Image, palette: np.ndarray):
    img_array = np.array(image.convert('RGB'), dtype=np.float32)
    height, width, _ = img_array.shape
    for y in range(height):
        for x in range(width):
            old_pixel = img_array[y, x].copy()
            new_pixel = palette[np.argmin(np.sqrt(np.sum((palette - old_pixel)**2, axis=1)))]
            img_array[y, x] = new_pixel
            quant_error = old_pixel - new_pixel
            if x + 1 < width: img_array[y, x + 1] += quant_error * 7 / 16
            if y + 1 < height:
                if x > 0: img_array[y + 1, x - 1] += quant_error * 3 / 16
                img_array[y + 1, x] += quant_error * 5 / 16
                if x + 1 < width: img_array[y + 1, x + 1] += quant_error * 1 / 16
    return Image.fromarray(np.uint8(img_array))

def image_to_bw_data(image: Image.Image):
    byte_width = (image.width + 7) // 8
    buffer = bytearray(byte_width * image.height)
    for y in range(image.height):
        for x in range(image.width):
            r, _, _ = image.getpixel((x, y))
            if r > 128: buffer[y * byte_width + x // 8] |= (1 << (7 - (x % 8)))
    return bytes(buffer)

def image_to_bwr_data(image: Image.Image):
    width, height = image.width, image.height
    byte_width = (width + 7) // 8
    b_buffer = bytearray(height * byte_width)
    r_buffer = bytearray(height * byte_width)
    for y in range(height):
        for x in range(width):
            r, g, b = image.getpixel((x, y))
            byte_index = y * byte_width + x // 8
            bit_index = 7 - (x % 8)
            if r < 128 and g < 128 and b < 128: # Black
                r_buffer[byte_index] |= (1 << bit_index)
            elif r > 128 and g > 128 and b > 128: # White
                b_buffer[byte_index] |= (1 << bit_index)
                r_buffer[byte_index] |= (1 << bit_index)
            else: # Red
                b_buffer[byte_index] |= (1 << bit_index)
    return bytes(b_buffer) + bytes(r_buffer)

async def send_command(client, cmd, data=None, with_response=True):
    payload = bytearray([cmd])
    if data: payload.extend(data)
    await client.write_gatt_char(CHARACTERISTIC_UUID, payload, response=with_response)

async def write_image_data(client, image_data, mtu_size, step='bw'):
    logger.info(f"Writing image data (step: {step}) with MTU size: {mtu_size}")
    chunk_size = mtu_size - 2
    if chunk_size <= 0:
        logger.error(f"MTU size {mtu_size} is too small to send data.")
        return
    interleaved_count = 10
    no_reply_count = interleaved_count
    total_chunks = (len(image_data) + chunk_size - 1) // chunk_size
    for i in range(0, len(image_data), chunk_size):
        chunk = image_data[i:i + chunk_size]
        header = (0x0F if step == 'bw' else 0x00) | (0x00 if i == 0 else 0xF0)
        data_payload = bytearray([header])
        data_payload.extend(chunk)
        with_response = no_reply_count <= 0
        logger.info(f"⇑ Sending chunk {i // chunk_size + 1}/{total_chunks} (header: {header:02x}, with_response={with_response})")
        await send_command(client, EpdCmd.WRITE_IMG, data_payload, with_response=with_response)
        if with_response:
            no_reply_count = interleaved_count
            await asyncio.sleep(0.05)
        else:
            no_reply_count -= 1

def render_text_to_image(lines, width, height, font_path, font_size, color):
    image = Image.new('RGB', (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype(font_path, font_size)
    except IOError:
        logger.warning(f"Font not found at {font_path}. Using default font.")
        font = ImageFont.load_default()
    y_text = 0
    for line in lines:
        bbox = font.getbbox(line)
        line_height = bbox[3] - bbox[1]
        fill_color = (255, 0, 0) if color.lower() == 'red' else (0, 0, 0)
        draw.text((0, y_text), line, font=font, fill=fill_color)
        y_text += line_height + 2
    return image

async def main_logic(address, adapter, image_path, text, font, size, color, width, height, clear, color_mode, dither):
    mtu_size_from_device = 0
    resolution_from_device = None
    config_event = asyncio.Event()
    mtu_event = asyncio.Event()
    msg_index = 0

    def notification_handler(sender, data):
        nonlocal mtu_size_from_device, msg_index, resolution_from_device
        if msg_index == 0:
            logger.info(f"⇓ Received config: {data.hex()}")
            if len(data) >= 8:
                driver_byte = data[7]
                resolution = DRIVER_TO_RESOLUTION.get(driver_byte)
                if resolution:
                    resolution_from_device = resolution
                    logger.info(f"Detected driver 0x{driver_byte:02x}, setting resolution to {resolution}")
                else:
                    logger.warning(f"Unknown driver byte 0x{driver_byte:02x}, resolution not set.")
            config_event.set()
        else:
            try:
                decoded_data = data.decode('utf-8')
                if decoded_data.startswith('mtu='):
                    mtu_val = int(decoded_data.split('=')[1])
                    mtu_size_from_device = mtu_val
                    logger.info(f"MTU updated to: {mtu_size_from_device}")
                    if not mtu_event.is_set(): mtu_event.set()
            except UnicodeDecodeError: pass
        msg_index += 1

    logger.info(f"Attempting to connect to {address} using adapter {adapter or 'default'}...")
    client = BleakClient(address, adapter=adapter)
    try:
        await client.connect()
        logger.info(f"Connected to {client.address}")
        await client.start_notify(CHARACTERISTIC_UUID, notification_handler)
        logger.info("Started notifications, sending INIT to get config...")
        await send_command(client, EpdCmd.INIT)
        try:
            logger.info("Waiting for config and MTU from device (timeout 10s)...")
            await asyncio.wait_for(asyncio.gather(config_event.wait(), mtu_event.wait()), timeout=10.0)
        except asyncio.TimeoutError:
            logger.warning("Timed out waiting for config/MTU. Using defaults.")
            if not mtu_event.is_set(): mtu_size_from_device = client.mtu_size
        
        if resolution_from_device:
            width, height = resolution_from_device
        elif width is None or height is None:
            logger.error("Resolution could not be determined from device and was not provided. Aborting.")
            return

        logger.info(f"Using final resolution: {width}x{height}")

        if clear:
            logger.info("Sending Clear command...")
            await send_command(client, EpdCmd.CLEAR)
            await asyncio.sleep(2)

        if image_path:
            logger.info(f"Opening image: {image_path}")
            with Image.open(image_path) as img:
                img = img.resize((width, height))
        elif text:
            logger.info("Rendering text to image...")
            lines = text.split('\\n')
            img = render_text_to_image(lines, width, height, font, size, color)
        else:
            return

        if dither == 'floyd':
            logger.info("Applying Floyd-Steinberg dithering...")
            palette = THREE_COLOR_PALETTE if color_mode == 'bwr' else TWO_COLOR_PALETTE
            img = floyd_steinberg_dither(img, palette)

        if color_mode == 'bwr':
            logger.info("Processing image for Black/White/Red display...")
            epd_data = image_to_bwr_data(img)
            half_len = len(epd_data) // 2
            await write_image_data(client, epd_data[:half_len], mtu_size_from_device, step='bw')
            await write_image_data(client, epd_data[half_len:], mtu_size_from_device, step='red')
        else:
            logger.info("Processing image for Black/White display...")
            epd_data = image_to_bw_data(img)
            await write_image_data(client, epd_data, mtu_size_from_device, step='bw')
        
        logger.info("Sending Refresh command...")
        await send_command(client, EpdCmd.REFRESH)
        logger.info("Waiting for refresh to complete...")
        await asyncio.sleep(5)
        
    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
    finally:
        if client.is_connected:
            await client.stop_notify(CHARACTERISTIC_UUID)
            await client.disconnect()
            logger.info("Disconnected.")

@click.group()
def cli(): pass

@cli.command()
@click.option('--adapter', help='Bluetooth adapter to use, e.g., hci0')
def scan(adapter):
    async def scan_logic(adapter):
        print(f"Scanning for devices using adapter {adapter or 'default'}...")
        devices = await BleakScanner.discover(adapter=adapter)
        for d in devices: print(f"- {d.address}: {d.name}")
    asyncio.run(scan_logic(adapter))

@cli.command()
@click.option('--address', required=True, help='BLE device address.')
@click.option('--adapter', help='Bluetooth adapter to use, e.g., hci0')
@click.option('--image', 'image_path', type=click.Path(exists=True), help='Path to the image file.')
@click.option('--text', help='Text to display. Use "\\n" for new lines.')
@click.option('--font', default='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', help='Path to TTF font file.')
@click.option('--size', default=24, help='Font size.')
@click.option('--color', default='black', help='Text color (black or red).')
@click.option('--width', default=None, type=int, help='EPD width. Overrides auto-detection.')
@click.option('--height', default=None, type=int, help='EPD height. Overrides auto-detection.')
@click.option('--clear', is_flag=True, help='Clear the screen before sending.')
@click.option('--color-mode', type=click.Choice(['bw', 'bwr'], case_sensitive=False), default='bw', help='Color mode (bw or bwr for black/white/red).')
@click.option('--dither', type=click.Choice(['none', 'floyd'], case_sensitive=False), default='floyd', help='Dithering algorithm.')
def send(address, adapter, image_path, text, font, size, color, width, height, clear, color_mode, dither):
    if not image_path and not text:
        raise click.UsageError("Either --image or --text must be provided.")
    asyncio.run(main_logic(address, adapter, image_path, text, font, size, color, width, height, clear, color_mode, dither))

if __name__ == '__main__':
    cli()