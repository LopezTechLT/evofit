import os
import json
import math

FACES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'faces')
os.makedirs(FACES_DIR, exist_ok=True)


def register_face(client_id: int, embedding: list) -> bool:
    if not embedding or len(embedding) != 128:
        return False
    client_dir = os.path.join(FACES_DIR, str(client_id))
    os.makedirs(client_dir, exist_ok=True)
    count = len([f for f in os.listdir(client_dir) if f.endswith('.json')])
    path = os.path.join(client_dir, f'{count + 1}.json')
    with open(path, 'w') as f:
        json.dump(embedding, f)
    return True


def has_faces(client_id: int) -> bool:
    client_dir = os.path.join(FACES_DIR, str(client_id))
    return os.path.isdir(client_dir) and len([f for f in os.listdir(client_dir) if f.endswith('.json')]) > 0


def recognize(embedding: list, distance_threshold: float = 0.6):
    if not embedding or len(embedding) != 128:
        return None
    best_id = None
    best_dist = float('inf')
    for cid_str in os.listdir(FACES_DIR):
        cid_dir = os.path.join(FACES_DIR, cid_str)
        if not os.path.isdir(cid_dir):
            continue
        for fname in os.listdir(cid_dir):
            if not fname.endswith('.json'):
                continue
            path = os.path.join(cid_dir, fname)
            try:
                with open(path) as f:
                    stored = json.load(f)
            except Exception:
                continue
            dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(embedding, stored)))
            if dist < best_dist:
                best_dist = dist
                best_id = int(cid_str)
    if best_id is None or best_dist > distance_threshold:
        return None
    return best_id


def is_available() -> bool:
    return True
