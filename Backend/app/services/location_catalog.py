import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class SriLankaLocation:
    display_name: str
    latitude: float
    longitude: float
    aliases: tuple[str, ...]


# A deliberately small offline catalog for high-frequency attractions that are
# often described with booking words ("tickets", "safari cost", etc.). It
# avoids paid geocoding calls and keeps the planner usable when a free provider
# cannot match an activity label to its map feature.
SRI_LANKA_LOCATIONS = (
    SriLankaLocation(
        display_name="Sigiriya Rock Fortress, Sri Lanka",
        latitude=7.9566634,
        longitude=80.7599301,
        aliases=("sigiriya rock fortress", "lion rock sigiriya", "sigiriya"),
    ),
    SriLankaLocation(
        display_name="Minneriya National Park, Sri Lanka",
        latitude=8.0161446,
        longitude=80.8501390,
        aliases=("minneriya national park safari", "minneriya national park", "minneriya"),
    ),
    SriLankaLocation(
        display_name="Hiriwadunna Village Safari area near Habarana, Sri Lanka",
        latitude=8.0423226,
        longitude=80.7564622,
        aliases=(
            "hiriwadunna village safari",
            "hiriwadunna village",
            "hiriwadunna safari",
        ),
    ),
    SriLankaLocation(
        display_name="Dambulla Cave Temple, Sri Lanka",
        latitude=7.8566286,
        longitude=80.6484958,
        aliases=("dambulla cave temple", "golden temple dambulla"),
    ),
    SriLankaLocation(
        display_name="Pidurangala Rock, Sri Lanka",
        latitude=7.9660630,
        longitude=80.7616591,
        aliases=("pidurangala rock", "pidurangala"),
    ),
    SriLankaLocation(
        display_name="Ancient City of Polonnaruwa, Sri Lanka",
        latitude=7.9403,
        longitude=81.0188,
        aliases=("polonnaruwa ancient city", "ancient city of polonnaruwa", "polonnaruwa"),
    ),
    SriLankaLocation(
        display_name="Bahirawakanda Temple, Kandy, Sri Lanka",
        latitude=7.29553,
        longitude=80.63094,
        aliases=(
            "bahirawakanda vihara buddha statue",
            "bahirawakanda buddha",
            "bahirawakanda temple",
            "bahirawakanada temple",
        ),
    ),
    SriLankaLocation(
        display_name="Udawattakele Forest Reserve Main Entrance, Kandy, Sri Lanka",
        latitude=7.2936206,
        longitude=80.6441322,
        aliases=(
            "udawatta kele sanctuary",
            "udawattakele sanctuary",
            "udawattekele sanctuary",
            "udawattakele forest reserve",
            "udawatta kele forest reserve",
        ),
    ),
)


def normalize_location_text(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", ascii_value.lower()).split())


def lookup_sri_lanka_location(query: str) -> dict | None:
    normalized_query = normalize_location_text(query)
    matches: list[tuple[int, SriLankaLocation]] = []

    for location in SRI_LANKA_LOCATIONS:
        for alias in location.aliases:
            normalized_alias = normalize_location_text(alias)
            if normalized_query == normalized_alias or normalized_query.startswith(
                f"{normalized_alias} "
            ):
                matches.append((len(normalized_alias), location))

    if not matches:
        return None

    location = max(matches, key=lambda item: item[0])[1]
    return {
        "display_name": location.display_name,
        "latitude": location.latitude,
        "longitude": location.longitude,
        "provider": "local_catalog",
    }
