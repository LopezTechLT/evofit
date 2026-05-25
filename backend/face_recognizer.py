import os
from PIL import Image, ImageDraw
import io
import math

FACES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'faces')
FACE_SIZE = (100, 100)

os.makedirs(FACES_DIR, exist_ok=True)


def _detect_face(image_bytes: bytes):
    """Extract face region using center crop (assumes face is centered in frame)."""
    try:
        img = Image.open(io.BytesIO(image_bytes))
    except Exception:
        return None, None
    gray = img.convert('L')
    w, h = gray.size
    crop_size = min(w, h)
    left = (w - crop_size) // 2
    top = (h - crop_size) // 3
    right = left + crop_size
    bottom = top + crop_size
    face = gray.crop((left, top, right, bottom))
    preview = img.copy()
    draw = ImageDraw.Draw(preview)
    draw.rectangle([left, top, right, bottom], outline=(0, 255, 0), width=3)
    buf = io.BytesIO()
    preview.save(buf, format='JPEG')
    return face, buf.getvalue()


def _vectorize(face_image):
    """Convert face image to flat list of pixel values."""
    resized = face_image.resize(FACE_SIZE)
    return list(resized.getdata())


def register_face(client_id: int, image_bytes: bytes) -> bool:
    face_region, _ = _detect_face(image_bytes)
    if face_region is None:
        return False
    client_dir = os.path.join(FACES_DIR, str(client_id))
    os.makedirs(client_dir, exist_ok=True)
    count = len([f for f in os.listdir(client_dir) if f.endswith('.jpg')])
    path = os.path.join(client_dir, f'{count + 1}.jpg')
    face_region.save(path)
    return True


def has_faces(client_id: int) -> bool:
    client_dir = os.path.join(FACES_DIR, str(client_id))
    return os.path.isdir(client_dir) and len([f for f in os.listdir(client_dir) if f.endswith('.jpg')]) > 0


def recognize(image_bytes: bytes, distance_threshold: float = 4500.0):
    face_region, preview = _detect_face(image_bytes)
    if face_region is None:
        return None, None
    query_vec = _vectorize(face_region)
    best_id = None
    best_dist = float('inf')
    for cid_str in os.listdir(FACES_DIR):
        cid_dir = os.path.join(FACES_DIR, cid_str)
        if not os.path.isdir(cid_dir):
            continue
        for fname in os.listdir(cid_dir):
            if not fname.endswith('.jpg'):
                continue
            path = os.path.join(cid_dir, fname)
            try:
                img = Image.open(path).convert('L')
            except Exception:
                continue
            stored_vec = _vectorize(img)
            dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(query_vec, stored_vec)))
            if dist < best_dist:
                best_dist = dist
                best_id = int(cid_str)
    if best_id is None or best_dist > distance_threshold:
        return None, None
    return best_id, preview


def is_available() -> bool:
    return True
