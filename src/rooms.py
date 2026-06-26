from math import ceil
from src.schemas import RoomConfig, HotelPreferences


def suggest_room_config(group_type: str, n: int, prefs: HotelPreferences) -> RoomConfig:
    g = (group_type or "").lower()
    bed = "double" if prefs.bed_when_sharing == "double" else "twin"

    if n <= 1:
        return RoomConfig(rooms=1, description="1 room for 1 person",
                          bed_types="1 single/double bed")
    if g == "couple":
        return RoomConfig(rooms=1, description="1 room for the couple",
                          bed_types="1 double bed")
    if g == "family":
        rooms = max(1, ceil(n / 2))
        return RoomConfig(rooms=rooms,
                          description=f"{rooms} room(s) for the family ({n} people)",
                          bed_types="double beds + extra beds as needed")

    # friends / colleagues / mixed
    if prefs.non_couples_sharing == "separate":
        return RoomConfig(rooms=n, description=f"{n} separate rooms (one per person)",
                          bed_types="1 single bed each")
    rooms = ceil(n / 2)
    return RoomConfig(rooms=rooms, description=f"{rooms} room(s), up to 2 sharing each",
                      bed_types=f"{bed} bed(s)")