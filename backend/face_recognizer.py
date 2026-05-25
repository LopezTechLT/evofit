import os
import cv2
import numpy as np
from PIL import Image

FACES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'faces')
TRAINER_FILE = os.path.join(FACES_DIR, 'trainer.yml')
CASCADE_PATH = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'

os.makedirs(FACES_DIR, exist_ok=True)

def _detect_face(image_bytes: bytes):
    img_array = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    if img is None:
        return None, None
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    face_cascade = cv2.CascadeClassifier(CASCADE_PATH)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80))
    if len(faces) == 0:
        return None, None
    (x, y, w, h) = faces[0]
    face_region = gray[y:y + h, x:x + w]
    # Draw rectangle on copy for preview
    preview = img.copy()
    cv2.rectangle(preview, (x, y), (x + w, y + h), (0, 255, 0), 2)
    _, preview_bytes = cv2.imencode('.jpg', preview)
    return face_region, preview_bytes.tobytes()

def register_face(client_id: int, image_bytes: bytes) -> bool:
    face_region, _ = _detect_face(image_bytes)
    if face_region is None:
        return False
    client_dir = os.path.join(FACES_DIR, str(client_id))
    os.makedirs(client_dir, exist_ok=True)
    count = len([f for f in os.listdir(client_dir) if f.endswith('.jpg')])
    path = os.path.join(client_dir, f'{count + 1}.jpg')
    cv2.imwrite(path, face_region)
    _retrain()
    return True

def has_faces(client_id: int) -> bool:
    client_dir = os.path.join(FACES_DIR, str(client_id))
    return os.path.isdir(client_dir) and len([f for f in os.listdir(client_dir) if f.endswith('.jpg')]) > 0

def _retrain():
    faces = []
    ids = []
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
            faces.append(img)
            ids.append(int(cid_str))
    if not faces:
        return
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.train(faces, np.array(ids))
    recognizer.write(TRAINER_FILE)

def recognize(image_bytes: bytes, confidence_threshold: float = 55.0):
    if not os.path.exists(TRAINER_FILE):
        return None, None
    face_region, preview = _detect_face(image_bytes)
    if face_region is None:
        return None, None
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read(TRAINER_FILE)
    cid, conf = recognizer.predict(face_region)
    if conf > confidence_threshold:
        return None, None
    return int(cid), preview
