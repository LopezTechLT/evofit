from __future__ import annotations

import re

from flask import request
from flask_login import current_user

from app import db
from app.models import Gym


def slugify_gym_name(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (name or "").strip().lower()).strip("-")
    return slug or "gym"


def get_default_gym() -> Gym:
    gym = Gym.query.order_by(Gym.id.asc()).first()
    if gym:
        return gym
    gym = Gym(name="Gym Principal", slug="principal", plan="starter")
    db.session.add(gym)
    db.session.commit()
    return gym


def get_gyms_for_select() -> list[Gym]:
    gyms = Gym.query.order_by(Gym.name.asc()).all()
    return gyms if gyms else [get_default_gym()]


def get_gym_by_slug(slug: str | None) -> Gym | None:
    if not slug:
        return None
    return Gym.query.filter_by(slug=slug.strip().lower()).first()


def extract_subdomain_slug() -> str | None:
    host = (request.host or "").split(":")[0].strip().lower()
    if not host or host in ("localhost", "127.0.0.1"):
        return None
    parts = [p for p in host.split(".") if p]
    if len(parts) < 2:
        return None
    subdomain = parts[0]
    if subdomain in ("www", "app"):
        return None
    return subdomain


def resolve_request_gym(selected_slug: str | None = None) -> Gym:
    if current_user.is_authenticated and getattr(current_user, "gym_id", None):
        gym = Gym.query.get(current_user.gym_id)
        if gym:
            return gym
    gym = get_gym_by_slug(extract_subdomain_slug())
    if gym:
        return gym
    gym = get_gym_by_slug(selected_slug)
    if gym:
        return gym
    return get_default_gym()


def get_current_gym_id(selected_slug: str | None = None) -> int:
    return int(resolve_request_gym(selected_slug).id)
