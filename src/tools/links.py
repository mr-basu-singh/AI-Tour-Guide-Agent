from urllib.parse import quote_plus


def bus_booking_links(from_place: str, to_place: str) -> list:
    f = from_place.split(",")[0].strip().lower().replace(" ", "-")
    t = to_place.split(",")[0].strip().lower().replace(" ", "-")
    fq = quote_plus(from_place.split(",")[0].strip())
    tq = quote_plus(to_place.split(",")[0].strip())
    return [
        {"site": "redBus", "url": f"https://www.redbus.in/bus-tickets/{f}-to-{t}"},
        {"site": "MakeMyTrip", "url": f"https://www.makemytrip.com/bus-tickets/{f}-{t}-bus-ticket-booking.html"},
        {"site": "AbhiBus", "url": f"https://www.abhibus.com/bus-tickets/{fq}-to-{tq}"},
    ]


def train_booking_links(from_place: str, to_place: str) -> list:
    fq = quote_plus(from_place)
    tq = quote_plus(to_place)
    return [
        {"site": "IRCTC", "url": "https://www.irctc.co.in"},
        {"site": "ConfirmTkt", "url": f"https://www.confirmtkt.com/train-between-stations/{fq}-to-{tq}"},
        {"site": "MakeMyTrip", "url": f"https://www.makemytrip.com/railways/"},
    ]


def flight_booking_links(from_place: str, to_place: str) -> list:
    fq = quote_plus(from_place)
    tq = quote_plus(to_place)
    return [
        {"site": "Google Flights", "url": f"https://www.google.com/travel/flights?q=flights+from+{fq}+to+{tq}"},
        {"site": "MakeMyTrip", "url": f"https://www.makemytrip.com/flights/"},
        {"site": "Skyscanner", "url": f"https://www.skyscanner.co.in/transport/flights/{fq}/{tq}/"},
    ]


def cab_links(from_place: str, to_place: str) -> list:
    fq = quote_plus(from_place)
    tq = quote_plus(to_place)
    return [
        {"site": "Google Maps", "url": f"https://www.google.com/maps/dir/{fq}/{tq}"},
    ]


def hotel_booking_links(place: str) -> list:
    pq = quote_plus(place)
    p = place.replace(" ", "+")
    return [
        {"site": "Booking.com", "url": f"https://www.booking.com/searchresults.html?ss={p}"},
        {"site": "MakeMyTrip", "url": f"https://www.makemytrip.com/hotels-in-{place.lower().replace(' ', '-')}.html"},
        {"site": "Goibibo", "url": f"https://www.goibibo.com/hotels/hotels-in-{place.lower().replace(' ', '-')}/"},
    ]


def booking_links_for_leg(leg: dict) -> list:
    mode = (leg.get("mode") or "").lower()
    f, t = leg.get("from_place", ""), leg.get("to_place", "")
    if "bus" in mode:
        return bus_booking_links(f, t)
    if "train" in mode:
        return train_booking_links(f, t)
    if "flight" in mode or "fly" in mode:
        return flight_booking_links(f, t)
    if "cab" in mode or "taxi" in mode:
        return cab_links(f, t)
    return cab_links(f, t)