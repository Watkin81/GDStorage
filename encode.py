from curl_cffi import requests
from PIL import Image
import json
import base64
import io
import hashlib
import gzip
import sys
import os

# Config
BLOCK_IDS = [5, 73, 80, 120, 211, 1820, 259, 266, 273, 1142, 477, 485, 644, 752, 815, 817]
ROTATIONS = list(range(16))
SCALES = [round(0.5 + 0.25*i, 2) for i in range(12)]

# Functions
def xor_cipher(text: str, key: str) -> str:
    out = []
    for i, c in enumerate(text):
        out.append(chr(ord(c) ^ ord(key[i % len(key)])))
    return ''.join(out)

def generate_seed2(level_string: str) -> str:
    if len(level_string) < 50:
        while len(level_string) < 50:
            level_string += level_string
        level_string = level_string[:50]
    
    space = len(level_string) // 50
    seed_raw = "".join(level_string[space * i] for i in range(50))
    seed_raw += "xI25fpAapCQg"
    
    hashed = hashlib.sha1(seed_raw.encode()).hexdigest()
    xored = xor_cipher(hashed, "41274")
    return base64.urlsafe_b64encode(xored.encode()).decode()

def decompress_level_string(compressed):
    try:
        standard_b64 = compressed.replace('-', '+').replace('_', '/')
        padding = len(standard_b64) % 4
        if padding:
            standard_b64 += '=' * (4 - padding)
        decoded = base64.b64decode(standard_b64)
        return gzip.decompress(decoded).decode()
    except:
        return None

def compress_level_string(decompressed_data):
    compressed = gzip.compress(decompressed_data.encode(), compresslevel=9)
    standard_b64 = base64.b64encode(compressed).decode()
    return standard_b64.replace('+', '-').replace('/', '_').rstrip('=')

def byte_to_block_params(byte_value):
    block_index = byte_value % len(BLOCK_IDS)
    rotation_index = (byte_value // len(BLOCK_IDS)) % len(ROTATIONS)
    scale_index = (byte_value // (len(BLOCK_IDS) * len(ROTATIONS))) % len(SCALES)
    return BLOCK_IDS[block_index], rotation_index, SCALES[scale_index]

def encode_data_to_visual_objects(data_bytes, file_type_code, start_x=75, start_y=0):
    objects = [f"1,1,2,{start_x},3,{start_y},108,{0xDEADBEEF},109,{len(data_bytes)},110,{file_type_code}"]
    
    for i, byte_val in enumerate(data_bytes):
        block_id, rotation_index, scale = byte_to_block_params(byte_val)
        rotation_degrees = rotation_index * 22.5
        grid_x = start_x + (i // 10) * 30
        grid_y = start_y + (i % 10) * 30
        
        objects.append(f"1,{block_id},2,{grid_x},3,{grid_y},6,{rotation_degrees},128,{scale},129,{scale}")
    
    return ';'.join(objects) + ';'

def detect_file_type(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    types = {
        ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'): ('image', 1),
        ('.txt', '.md', '.log'): ('text', 2),
        ('.pdf',): ('pdf', 3),
        ('.json',): ('json', 4)
    }
    for exts, (name, code) in types.items():
        if ext in exts:
            return name, code
    return 'binary', 5

# Load credentials file
try:
    with open('exampleCredentials.json', 'r') as f:
        creds = json.load(f)
except Exception as e:
    print(f"Error: Could not load credentials.json - {e}")
    sys.exit(1)

# Base level string
BASE_LEVEL = 'H4sIAAAAAAAACqWTy43DMAxEG9ICHJLyBzmlhhQwBaSFLX5FjY82NkYO5ljm8Ikk4Pcrtgam0QnvDHrvBCQu0cfkD7gQZsaVIHqFjcaN-AUnwvwzBL5H7KeI8qjgI4iz6s9At1Yyzt8z8nInGsf-G6ZfDnMDslxCbq72bJz2fiKalXTJIsk2ot7XGf3I68St5BW7cjOKMxPPnFFZmExyuWwuh68NZTcJJD7FhXJRQrlQLtRaCpaCZVe5chFypkTth-6rf6xkn4JjCtX50S7U_JBHXe1t4KMC-ngef1FdDV2pAwAA'

base_decompressed = decompress_level_string(BASE_LEVEL)
if not base_decompressed:
    base_decompressed = "kS38,1,2,15,3,15;kS38,1,2,45,3,15;kS38,1,2,75,3,15;"

# File input
file_path = input("File path: ").strip().strip('"')

if not os.path.exists(file_path):
    print(f"Error: File not found")
    sys.exit(1)

file_type_name, file_type_code = detect_file_type(file_path)

try:
    if file_type_name == 'image':
        img = Image.open(file_path)
        
        # Resize if needed
        max_dimension = 512
        if img.size[0] > max_dimension or img.size[1] > max_dimension:
            img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
        
        # Compress as JPEG
        img_byte_arr = io.BytesIO()
        if img.mode in ('RGBA', 'LA', 'P'):
            rgb_img = Image.new('RGB', img.size, (255, 255, 255))
            rgb_img.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            rgb_img.save(img_byte_arr, format='JPEG', quality=40, optimize=True)
        else:
            img.save(img_byte_arr, format='JPEG', quality=40, optimize=True)
        
        file_bytes = img_byte_arr.getvalue()
        print(f"Image: {img.size[0]}x{img.size[1]}px, {len(file_bytes):,} bytes")
    else:
        with open(file_path, 'rb') as f:
            file_bytes = f.read()
        print(f"File: {len(file_bytes):,} bytes")

    # Encode
    visual_objects = encode_data_to_visual_objects(file_bytes, file_type_code)
    
    # Combine and compress
    if not base_decompressed.endswith(';'):
        base_decompressed += ';'
    modified_decompressed = base_decompressed + visual_objects
    modified_level_string = compress_level_string(modified_decompressed)
    
    object_count = len(file_bytes) + 1
    seed2 = generate_seed2(modified_level_string)
    
    print(f"Objects: {object_count:,}")

except Exception as e:
    print(f"Error processing file: {e}")
    sys.exit(1)

# Upload
level_name = input("Level name: ").strip()

data = {
    'accountID': creds.get('accountID', ''),
    'audioTrack': '0',
    'auto': '0',
    'binaryVersion': '45',
    'coins': '0',
    'gameVersion': '22',
    'gjp2': creds.get('gjp2', ''),
    'ldm': '0',
    'levelDesc': base64.urlsafe_b64encode(b'GDFileStorage').decode(),
    'levelID': '0',
    'levelInfo': '',
    'levelLength': '0',
    'levelName': level_name,
    'levelString': modified_level_string,
    'levelVersion': '1',
    'objects': str(object_count),
    'original': '0',
    'password': '0',
    'requestedStars': '0',
    'secret': 'Wmfd2893gb7',
    'seed': '0C9a9Vl1YJ',
    'seed2': seed2,
    'songID': '0',
    'ts': '0',
    'twoPlayer': '0',
    'udid': creds.get('udid', ''),
    'unlisted': '2',
    'userName': creds.get('username', ''),
    'uuid': creds.get('uuid', ''),
    'wt': '0',
    'wt2': '7'
} # From docs

try:
    response = requests.post(
        "http://www.boomlings.com/database/uploadGJLevel21.php",
        data=data,
        headers={"User-Agent": "", "Content-Type": "application/x-www-form-urlencoded"},
        timeout=30
    )

    if response.text.isdigit():
        print(f"\n+ Success! Level ID: {response.text}")
    elif response.text == "-1":
        print("\n- Upload failed (server returned -1)")
    else:
        print(f"\n- Error: {response.text}")

except Exception as e:
    print(f"\n- Request failed: {e}")
