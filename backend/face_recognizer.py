import json
import math
from backend import db
from backend.models import FaceEmbedding


def register_face(client_id: int, embedding: list) -> bool:
    if not embedding or len(embedding) != 128:
        return False
    fe = FaceEmbedding(client_id=client_id, embedding=json.dumps(embedding))
    db.session.add(fe)
    db.session.commit()
    return True


def has_faces(client_id: int) -> bool:
    return FaceEmbedding.query.filter_by(client_id=client_id).count() > 0


def recognize(embedding: list, distance_threshold: float = 0.4):
    if not embedding or len(embedding) != 128:
        return None
    all_faces = FaceEmbedding.query.all()
    if not all_faces:
        return None
    best_id = None
    best_dist = float('inf')
    for fe in all_faces:
        try:
            stored = json.loads(fe.embedding)
        except Exception:
            continue
        if len(stored) != 128:
            continue
        dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(embedding, stored)))
        if dist < best_dist:
            best_dist = dist
            best_id = fe.client_id
    if best_id is None or best_dist > distance_threshold:
        return None
    return best_id


def is_available() -> bool:
    return True
