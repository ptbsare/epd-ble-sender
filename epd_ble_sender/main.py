import asyncio
import click
from bleak import BleakClient, BleakScanner
from PIL import Image, ImageDraw, ImageFont, ImageOps
import logging
import sys
import numpy as np
import re

# Constants
SERVICE_UUID = "62750001-d828-918d-fb46-b6c11c675aec"
CHARACTERISTIC_UUID = "62750002-d828-918d-fb46-b6c11c675aec"

DRIVER_TO_RESOLUTION = {
    0x00: (296, 128), 0x01: (250, 122), 0x02: (400, 300), 
    0x03: (400, 300), 0x04: (800, 480),
}

# Palettes
THREE_COLOR_PALETTE = np.array([[0, 0, 0], [255, 255, 255], [255, 0, 0]])
TWO_COLOR_PALETTE = np.array([[0, 0, 0], [255, 255, 255]])

class EpdCmd:
    INIT = 0x01; CLEAR = 0x02; REFRESH = 0x05; WRITE_IMG = 0x30

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', stream=sys.stdout)
logger = logging.getLogger(__name__)

# --- Dithering Algorithms ---

def find_closest_color(pixel, palette):
    return palette[np.argmin(np.sqrt(np.sum((palette - pixel)**2, axis=1)))]

def dither(image: Image.Image, palette: np.ndarray, algorithm: str):
    img_array = np.array(image.convert('RGB'), dtype=np.float32)
    height, width, _ = img_array.shape

    matrices = {
        'floyd': ([[0, 0, 7], [3, 5, 1]], 16),
        'jarvis': ([[0,0,0,7,5],[3,5,7,5,3],[1,3,5,3,1]], 48),
        'stucki': ([[0,0,0,8,4],[2,4,8,4,2],[1,2,4,2,1]], 42),
        'atkinson': ([[0,0,1,1],[1,1,1,0],[0,1,0,0]], 8)
    }
    
    matrix, divisor = matrices[algorithm]
    matrix_h, matrix_w = len(matrix), len(matrix[0])
    center_x = matrix_w // 2

    for y in range(height):
        for x in range(width):
            old_pixel = img_array[y, x].copy()
            new_pixel = find_closest_color(old_pixel, palette)
            img_array[y, x] = new_pixel
            quant_error = old_pixel - new_pixel

            for my in range(matrix_h):
                for mx in range(matrix_w):
                    if matrix[my][mx] == 0: continue
                    px, py = x + mx - center_x, y + my
                    if 0 <= px < width and 0 <= py < height:
                        img_array[py, px] += quant_error * matrix[my][mx] / divisor
    
    return Image.fromarray(np.clip(img_array, 0, 255).astype(np.uint8))

def bayer_dither(image: Image.Image, palette: np.ndarray):
    bayer_matrix = np.array([
        [ 0, 32,  8, 40,  2, 34, 10, 42], [48, 16, 56, 24, 50, 18, 58, 26],
        [12, 44,  4, 36, 14, 46,  6, 38], [60, 28, 52, 20, 62, 30, 54, 22],
        [ 3, 35, 11, 43,  1, 33,  9, 41], [51, 19, 59, 27, 49, 17, 57, 25],
        [15, 47,  7, 39, 13, 45,  5, 37], [63, 31, 55, 23, 61, 29, 53, 21]])
    
    img_array = np.array(image.convert('RGB'), dtype=np.float32)
    height, width, _ = img_array.shape
    
    for y in range(height):
        for x in range(width):
            threshold = (bayer_matrix[y % 8, x % 8] / 64.0 - 0.5) * 50
            pixel = np.clip(img_array[y, x] + threshold, 0, 255)
            img_array[y, x] = find_closest_color(pixel, palette)
            
    return Image.fromarray(img_array.astype(np.uint8))

# --- Image to Buffer Conversion ---

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

# --- BLE Communication ---

async def send_command(client, cmd, data=None, with_response=True):
    payload = bytearray([cmd])
    if data: payload.extend(data)
    await client.write_gatt_char(CHARACTERISTIC_UUID, payload, response=with_response)

async def write_image_data(client, image_data, mtu_size, interleaved_count, step='bw'):
    logger.info(f"Writing image data (step: {step}) with MTU size: {mtu_size}, interleaved count: {interleaved_count}")
    chunk_size = mtu_size - 2
    if chunk_size <= 0: return
    no_reply_count = interleaved_count
    total_chunks = (len(image_data) + chunk_size - 1) // chunk_size
    for i in range(0, len(image_data), chunk_size):
        chunk = image_data[i:i + chunk_size]
        header = (0x0F if step == 'bw' else 0x00) | (0x00 if i == 0 else 0xF0)
        data_payload = bytearray([header])
        data_payload.extend(chunk)
        
        is_last_chunk = (i + chunk_size) >= len(image_data)
        with_response = (no_reply_count <= 1 and interleaved_count > 0) or is_last_chunk

        logger.info(f"⇑ Sending chunk {i // chunk_size + 1}/{total_chunks} (header: {header:02x}, with_response={with_response})")
        await send_command(client, EpdCmd.WRITE_IMG, data_payload, with_response=with_response)
        
        if with_response:
            no_reply_count = interleaved_count
            await asyncio.sleep(0.05)
        else:
            no_reply_count -= 1

# --- Main Logic ---

def parse_line_markup(line):
    """Parses a line for [key=value, ...] markup."""
    markup_match = re.match(r'^\s*\[(.*?)\]\s*(.*)', line)
    if not markup_match:
        return {}, line

    markup_str, text = markup_match.groups()
    props = {}
    for part in markup_str.split(','):
        if '=' in part:
            key, value = part.split('=', 1)
            props[key.strip()] = value.strip()
    return props, text

def render_text_to_image(text_content, width, height, default_font_path, default_font_size, default_color):
    image = Image.new('RGB', (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    y_text = 0
    
    cached_fonts = {}

    for line in text_content.splitlines():
        props, text = parse_line_markup(line)

        # Determine properties for the current line
        font_size = int(props.get('size', default_font_size))
        font_path = props.get('font', default_font_path)
        color = props.get('color', default_color)
        align = props.get('align', 'left')

        # Load font, caching to avoid reloading
        font_key = (font_path, font_size)
        if font_key not in cached_fonts:
            try:
                cached_fonts[font_key] = ImageFont.truetype(font_path, font_size)
            except IOError:
                logger.warning(f"Could not load font {font_path}. Using default.")
                cached_fonts[font_key] = ImageFont.load_default()
        font = cached_fonts[font_key]

        # Calculate text position
        bbox = font.getbbox(text)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        x_text = 0
        if align == 'center':
            x_text = (width - text_width) / 2
        elif align == 'right':
            x_text = width - text_width

        # Draw text
        fill_color = (255, 0, 0) if color.lower() == 'red' else (0, 0, 0)
        draw.text((x_text, y_text), text, font=font, fill=fill_color)
        y_text += text_height + 2 # Add a small padding

    return image

async def main_logic(address, adapter, image_path, text, font, size, color, width, height, clear, color_mode, dither_algo, resize_mode, interleaved_count):
    mtu_size_from_device = 0
    resolution_from_device = None
    config_event, mtu_event = asyncio.Event(), asyncio.Event()
    msg_index = 0

    def notification_handler(sender, data):
        nonlocal mtu_size_from_device, msg_index, resolution_from_device
        if msg_index == 0:
            logger.info(f"⇓ Received config: {data.hex()}")
            if len(data) >= 12: # sizeof(epd_config_t) is at least 12
                config = {
                    'mosi_pin': data[0], 'sclk_pin': data[1], 'cs_pin': data[2],
                    'dc_pin': data[3], 'rst_pin': data[4], 'busy_pin': data[5],
                    'bs_pin': data[6], 'model_id': data[7], 'wakeup_pin': data[8],
                    'led_pin': data[9], 'en_pin': data[10], 'display_mode': data[11]
                }
                logger.info(f"  Parsed config: {config}")
                
                driver_byte = config['model_id']
                resolution = DRIVER_TO_RESOLUTION.get(driver_byte)
                if resolution:
                    resolution_from_device = resolution
                    logger.info(f"Detected driver 0x{driver_byte:02x}, setting resolution to {resolution}")
                else:
                    logger.warning(f"Unknown driver 0x{driver_byte:02x}")
            else:
                logger.warning(f"Received config is too short ({len(data)} bytes)")

            config_event.set()
        else:
            try:
                decoded_data = data.decode('utf-8')
                if decoded_data.startswith('mtu='):
                    mtu_size_from_device = int(decoded_data.split('=')[1])
                    logger.info(f"MTU updated to: {mtu_size_from_device}")
                    if not mtu_event.is_set(): mtu_event.set()
            except UnicodeDecodeError: 
                logger.warning(f"Received non-config notification that is not UTF-8: {data.hex()}")
        msg_index += 1

    logger.info(f"Attempting to connect to {address} using adapter {adapter or 'default'}...")
    client = BleakClient(address, adapter=adapter)
    try:
        await client.connect()
        logger.info(f"Connected to {client.address}")
        await client.start_notify(CHARACTERISTIC_UUID, notification_handler)
        await send_command(client, EpdCmd.INIT)
        try:
            await asyncio.wait_for(asyncio.gather(config_event.wait(), mtu_event.wait()), timeout=10.0)
        except asyncio.TimeoutError:
            logger.warning("Timed out waiting for config/MTU. Using defaults.")
            if not mtu_event.is_set(): mtu_size_from_device = client.mtu_size
        
        if width is None and height is None:
            if resolution_from_device:
                width, height = resolution_from_device
            else:
                logger.error("Resolution could not be determined. Please specify with --width and --height.")
                return
        logger.info(f"Using final resolution: {width}x{height}")

        if clear:
            await send_command(client, EpdCmd.CLEAR); await asyncio.sleep(2)

        if image_path:
            logger.info(f"Opening image: {image_path}")
            with Image.open(image_path) as img:
                if resize_mode == 'fit':
                    img.thumbnail((width, height))
                    new_img = Image.new('RGB', (width, height), (255, 255, 255))
                    new_img.paste(img, ((width - img.width) // 2, (height - img.height) // 2))
                    img = new_img
                elif resize_mode == 'crop':
                    img = ImageOps.fit(img, (width, height), Image.Resampling.LANCZOS)
                else: # stretch
                    img = img.resize((width, height))
        elif text:
            img = render_text_to_image(text, width, height, font, size, color)
        else: return

        if dither_algo != 'none':
            logger.info(f"Applying {dither_algo} dithering...")
            palette = THREE_COLOR_PALETTE if color_mode == 'bwr' else TWO_COLOR_PALETTE
            if dither_algo == 'bayer':
                img = bayer_dither(img, palette)
            else:
                img = dither(img, palette, dither_algo)

        if color_mode == 'bwr':
            epd_data = image_to_bwr_data(img)
            half_len = len(epd_data) // 2
            await write_image_data(client, epd_data[:half_len], mtu_size_from_device, interleaved_count, step='bw')
            await write_image_data(client, epd_data[half_len:], mtu_size_from_device, interleaved_count, step='red')
        else:
            epd_data = image_to_bw_data(img)
            await write_image_data(client, epd_data, mtu_size_from_device, interleaved_count, step='bw')
        
        await send_command(client, EpdCmd.REFRESH); await asyncio.sleep(5)
        
    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
    finally:
        if client.is_connected:
            await client.stop_notify(CHARACTERISTIC_UUID)
            await client.disconnect()
            logger.info("Disconnected. Waiting for graceful shutdown...")
            await asyncio.sleep(2) # Give time for BLE stack to clean up
            logger.info("Shutdown complete.")


# --- CLI Definition ---

@click.group()
def cli(): pass

@cli.command()
@click.option('--adapter', help='Bluetooth adapter to use, e.g., hci0')
def scan(adapter):
    asyncio.run(BleakScanner.discover(adapter=adapter))

@cli.command()
@click.option('--address', required=True)
@click.option('--adapter')
@click.option('--image', 'image_path', type=click.Path(exists=True))
@click.option('--text')
@click.option('--font', default='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', help='Default font path.')
@click.option('--size', default=24, help='Default font size.')
@click.option('--color', default='black', help='Default text color (black or red).')
@click.option('--width', type=int)
@click.option('--height', type=int)
@click.option('--clear', is_flag=True)
@click.option('--color-mode', type=click.Choice(['bw', 'bwr']), default='bw')
@click.option('--dither', 'dither_algo', type=click.Choice(['none', 'floyd', 'atkinson', 'jarvis', 'stucki', 'bayer']), default='floyd')
@click.option('--resize-mode', type=click.Choice(['stretch', 'fit', 'crop']), default='stretch')
@click.option('--interleaved-count', default=62, type=int, help='Number of chunks to send before waiting for a response.')
def send(address, adapter, image_path, text, font, size, color, width, height, clear, color_mode, dither_algo, resize_mode, interleaved_count):
    if not image_path and not text: raise click.UsageError("Either --image or --text must be provided.")
    asyncio.run(main_logic(address, adapter, image_path, text, font, size, color, width, height, clear, color_mode, dither_algo, resize_mode, interleaved_count))

if __name__ == '__main__':
    cli()