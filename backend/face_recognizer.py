import os
import numpy as np

FACES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'faces')
FACE_SIZE = (100, 100)
_cv2 = None

os.makedirs(FACES_DIR, exist_ok=True)


def _get_cv2():
    global _cv2
    if _cv2 is None:
        try:
            import cv2
            _cv2 = cv2
        except ImportError:
            return None
    return _cv2


def _detect_face(image_bytes: bytes):
    cv2 = _get_cv2()
    if cv2 is None:
        return None, None
    cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    img_array = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    if img is None:
        return None, None
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    face_cascade = cv2.CascadeClassifier(cascade_path)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80))
    if len(faces) == 0:
        return None, None
    (x, y, w, h) = faces[0]
    face_region = gray[y:y + h, x:x + w]
    preview = img.copy()
    cv2.rectangle(preview, (x, y), (x + w, y + h), (0, 255, 0), 2)
    _, preview_bytes = cv2.imencode('.jpg', preview)
    return face_region, preview_bytes.tobytes()


def _vectorize(face_gray):
    cv2 = _get_cv2()
    if cv2 is None:
        return None
    resized = cv2.resize(face_gray, FACE_SIZE)
    return resized.flatten().astype(np.float32)


def register_face(client_id: int, image_bytes: bytes) -> bool:
    cv2 = _get_cv2()
    if cv2 is None:
        return False
    face_region, _ = _detect_face(image_bytes)
    if face_region is None:
        return False
    client_dir = os.path.join(FACES_DIR, str(client_id))
    os.makedirs(client_dir, exist_ok=True)
    count = len([f for f in os.listdir(client_dir) if f.endswith('.jpg')])
    path = os.path.join(client_dir, f'{count + 1}.jpg')
    cv2.imwrite(path, face_region)
    return True


def has_faces(client_id: int) -> bool:
    client_dir = os.path.join(FACES_DIR, str(client_id))
    return os.path.isdir(client_dir) and len([f for f in os.listdir(client_dir) if f.endswith('.jpg')]) > 0


def recognize(image_bytes: bytes, distance_threshold: float = 4500.0):
    cv2 = _get_cv2()
    if cv2 is None:
        return None, None
    face_region, preview = _detect_face(image_bytes)
    if face_region is None:
        return None, None
    query_vec = _vectorize(face_region)
    if query_vec is None:
        return None, None
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
            img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue
            stored_vec = _vectorize(img)
            if stored_vec is None:
                continue
            dist = np.linalg.norm(query_vec - stored_vec)
            if dist < best_dist:
                best_dist = dist
                best_id = int(cid_str)
    if best_id is None or best_dist > distance_threshold:
        return None, None
    return best_id, preview


def is_available() -> bool:
    return _get_cv2() is not None
