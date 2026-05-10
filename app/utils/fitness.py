from __future__ import annotations

from datetime import datetime, timedelta


LEVEL_TITLES: dict[int, str] = {
    1: 'Principiante',
    2: 'Aprendiz',
    3: 'Constante',
    4: 'Dedicado',
    5: 'Guerrero',
    6: 'Atleta',
    7: 'Fitness',
    8: 'Imparable',
    9: 'Elite',
    10: 'Titan',
    12: 'Campeón',
    15: 'Leyenda',
    20: 'Inmortal',
}


def compute_level_from_xp(xp: int) -> int:
    xp = int(xp or 0)
    return max(1, (xp // 250) + 1)


def compute_xp_to_next(level: int, xp: int) -> int:
    level = max(1, int(level or 1))
    xp = int(xp or 0)
    next_threshold = level * 250
    return max(0, next_threshold - xp)


def get_level_title(level: int) -> str:
    title = LEVEL_TITLES.get(level)
    if title:
        return title
    if level >= 20:
        return 'Inmortal'
    if level >= 15:
        return 'Leyenda'
    if level >= 10:
        return 'Titan'
    if level >= 5:
        return 'Guerrero'
    return 'Principiante'


def get_league_for_level(level: int) -> str:
    if level >= 15:
        return 'Titan'
    if level >= 10:
        return 'Oro'
    if level >= 5:
        return 'Plata'
    return 'Bronce'


def is_same_day(a: datetime, b: datetime) -> bool:
    return a.date() == b.date()


def is_yesterday(reference: datetime, candidate: datetime) -> bool:
    return candidate.date() == (reference.date() - timedelta(days=1))

