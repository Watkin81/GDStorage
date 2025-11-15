from curl_cffi import requests
from PIL import Image
import json
import base64
import io
import gzip
import sys
import os

# Config
BLOCK_IDS = [5, 73, 80, 120, 211, 1820, 259, 266, 273, 1142, 477, 485, 644, 752, 815, 817]
ROTATIONS = list(range(16))
SCALES = [round(0.5 + 0.25*i, 2) for i in range(12)]

FILE_TYPE_EXTENSIONS = {
    1: '.jpg',
    2: '.txt',
    3: '.pdf',
    4: '.json',
    5: '.bin'
}

# Functions
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

def parse_objects(level_string):
    objects = []
    for obj_str in level_string.split(';'):
        if not obj_str.strip():
            continue
        obj = {}
        parts = obj_str.split(',')
        for i in range(0, len(parts)-1, 2):
            try:
                key = int(parts[i])
                val = parts[i+1]
                obj[key] = val
            except:
                pass
        if obj:
            objects.append(obj)
    return objects

def block_params_to_byte(block_id, rotation_index, scale):
    try:
        block_index = BLOCK_IDS.index(block_id)
        scale_index = SCALES.index(scale)
        byte_value = block_index + (rotation_index * len(BLOCK_IDS)) + (scale_index * len(BLOCK_IDS) * len(ROTATIONS))
        return byte_value
    except:
        return 0

def extract_data_from_level(level_id):
    try:
        response = requests.post(
            "http://www.boomlings.com/database/downloadGJLevel22.php",
            data={'levelID': level_id, 'secret': 'Wmfd2893gb7'},
            headers={"User-Agent": "", "Content-Type": "application/x-www-form-urlencoded"},
            timeout=30
        ) # From docs
        
        if response.text == "-1":
            return None, "Level not found"
        
        # Format is key:value:key:value
        parts = response.text.split(':')
        level_data = {}
        for i in range(0, len(parts)-1, 2):
            level_data[parts[i]] = parts[i+1]
        
        level_string = level_data.get('4', '')
        if not level_string:
            return None, "No level data"
        
        decompressed = decompress_level_string(level_string)
        if not decompressed:
            return None, "Decompression failed"
        
        objects = parse_objects(decompressed)
        
        header = None
        data_objects = []
        
        for obj in objects:
            if obj.get(108) == str(0xDEADBEEF):
                header = obj
            elif header and obj.get(1) and obj.get(6) and obj.get(128):
                data_objects.append(obj)
        
        if not header:
            return None, "No header found"
        
        expected_len = int(header.get(109, 0))
        file_type_code = int(header.get(110, 5))
        
        data_objects.sort(key=lambda o: (float(o.get(2, 0)), float(o.get(3, 0))))
        
        data_bytes = bytearray()
        for obj in data_objects[:expected_len]:
            try:
                block_id = int(obj.get(1))
                rotation = float(obj.get(6, 0))
                scale_x = float(obj.get(128, 1.0))
                
                rotation_index = round(rotation / 22.5) % 16
                scale = round(scale_x, 2)
                
                byte_val = block_params_to_byte(block_id, rotation_index, scale)
                data_bytes.append(byte_val)
            except:
                data_bytes.append(0)
        
        return bytes(data_bytes), file_type_code
        
    except Exception as e:
        return None, str(e)

# Main
level_id = input("Level ID: ").strip()

data_bytes, result = extract_data_from_level(level_id)

if data_bytes is None:
    print(f"Error: {result}")
    sys.exit(1)

file_type_code = result
extension = FILE_TYPE_EXTENSIONS.get(file_type_code, '.bin')
output_path = f"extracted_{level_id}{extension}"

if file_type_code == 1:
    try:
        img = Image.open(io.BytesIO(data_bytes))
        img.save(output_path)
        print(f"+ Saved: {output_path}")
    except:
        with open(output_path, 'wb') as f:
            f.write(data_bytes)
        print(f"+ Saved: {output_path}")
else:
    with open(output_path, 'wb') as f:
        f.write(data_bytes)
    print(f"+ Saved: {output_path}")
