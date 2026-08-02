import re
from collections.abc import Iterable
from typing import Optional

from app.services.google_maps import google_maps_service
from app.services.location_catalog import lookup_sri_lanka_location
from app.services.map_http import map_http_client


class GeocoderService:
    BASE_URL = "https://nominatim.openstreetmap.org/search"
    PHOTON_BASE_URL = "https://photon.komoot.io/api/"
    # Exact AI labels often differ from the canonical OpenStreetMap name by a
    # suffix such as "statue" or "sanctuary". A few progressively broader,
    # cached lookups make real places routable without maintaining an endless
    # attraction catalog. Nominatim requests remain globally rate limited by
    # MapHttpClient.
    MAX_FREE_PROVIDER_ATTEMPTS = 6
    MAX_SECONDARY_PROVIDER_ATTEMPTS = 3

    _NOISE_PATTERNS = (
        r"\b(?:tickets?|entrance\s+fees?|entry\s+fees?|opening\s+hours?)\b",
        r"\b(?:price|cost|booking|official|history)\b",
        r"\b(?:safari|hike|walk|walking\s+tour|tour)\b(?=\s*(?:,|$))",
    )
    _GENERIC_PLACE_WORDS = {
        "and",
        "buddha",
        "complex",
        "fort",
        "garden",
        "gardens",
        "national",
        "nature",
        "of",
        "park",
        "reserve",
        "sanctuary",
        "sri",
        "statue",
        "temple",
        "the",
        "tower",
        "viewpoint",
    }

    def _clean_query(self, query: str) -> str:
        cleaned = query.strip()
        for pattern in self._NOISE_PATTERNS:
            cleaned = re.sub(pattern, " ", cleaned, flags=re.IGNORECASE)
        # OpenStreetMap data in Sri Lanka commonly uses British English. AI
        # suggestions often use the American spelling, which otherwise leaves
        # valid city-centre activities without coordinates.
        cleaned = re.sub(r"\bcity\s+center\b", "city centre", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\b(?:and|for)\b(?=\s*(?:,|$))", " ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s+,", ",", cleaned)
        cleaned = re.sub(r",\s*,+", ",", cleaned)
        return " ".join(cleaned.split()).strip(" ,")

    def _candidate_queries(self, queries: Iterable[str]) -> list[str]:
        candidates: list[str] = []

        for query in queries:
            if not query or not query.strip():
                continue
            cleaned = self._clean_query(query)
            for candidate in (cleaned, query.strip()):
                if candidate and candidate.casefold() not in {
                    existing.casefold() for existing in candidates
                }:
                    candidates.append(candidate)

        return candidates

    @staticmethod
    def _query_key(query: str) -> str:
        return " ".join(re.sub(r"[^\w]+", " ", query.casefold()).split())

    @staticmethod
    def valid_coordinate_pair(latitude: object, longitude: object) -> bool:
        try:
            latitude_value = float(latitude)
            longitude_value = float(longitude)
        except (TypeError, ValueError):
            return False

        return -90 <= latitude_value <= 90 and -180 <= longitude_value <= 180

    def _broader_place_names(self, name: str) -> list[str]:
        cleaned = self._clean_query(name)
        words = [word.strip(" ,;:()[]{}") for word in cleaned.split()]
        words = [word for word in words if word]
        if len(words) < 2:
            return []

        # Keep shortening the descriptive suffix while preserving the
        # distinctive leading name. A single final word is only useful when it
        # is long enough to be a genuine proper-name clue.
        minimum_words = 1 if len(words[0]) >= 5 else 2
        return [
            " ".join(words[:length])
            for length in range(len(words) - 1, minimum_words - 1, -1)
        ]

    def place_queries(
        self,
        *,
        name: str,
        destination: str,
        search_query: str | None = None,
        country: str = "Sri Lanka",
    ) -> list[str]:
        queries: list[str] = []
        seen: set[str] = set()

        def add(query: str | None) -> None:
            if not query or not query.strip():
                return
            cleaned = self._clean_query(query)
            key = self._query_key(cleaned)
            if cleaned and key not in seen:
                seen.add(key)
                queries.append(cleaned)

        add(search_query)
        add(f"{name}, {destination}, {country}")
        add(f"{name}, {country}")

        for broader_name in self._broader_place_names(name):
            add(f"{broader_name}, {destination}, {country}")

        return queries

    def geocode_place(
        self,
        *,
        name: str,
        destination: str,
        search_query: str | None = None,
        country: str = "Sri Lanka",
    ) -> Optional[dict]:
        return self.geocode_candidates(
            self.place_queries(
                name=name,
                destination=destination,
                search_query=search_query,
                country=country,
            ),
            country,
            expected_name=name,
        )

    def _nominatim_geocode(self, query: str, country: str) -> Optional[dict]:
        search_text = query.strip()

        if country.lower() not in search_text.lower():
            search_text = f"{search_text}, {country}"

        params = {
            "q": search_text,
            "format": "jsonv2",
            "limit": 1,
            "addressdetails": 1,
        }
        if country.casefold() == "sri lanka":
            params["countrycodes"] = "lk"

        try:
            results = map_http_client.get_json(
                self.BASE_URL,
                params=params,
                headers={"User-Agent": "MagicTripPlanner/1.0 academic-project"},
                timeout=12,
                cache_key=f"geocode:{search_text.lower()}",
                min_interval_seconds=1.1,
                context="Nominatim geocoding",
            )
        except Exception:
            return None

        if not isinstance(results, list) or not results:
            return None

        item = results[0]
        if not isinstance(item, dict):
            return None
        if not item.get("lat") or not item.get("lon"):
            return None

        return {
            "display_name": item.get("display_name"),
            "latitude": float(item["lat"]),
            "longitude": float(item["lon"]),
            "provider": "openstreetmap",
        }

    def _matches_expected_name(self, expected_name: str, result_text: str) -> bool:
        expected_words = [
            word
            for word in re.findall(r"\w+", expected_name.casefold())
            if len(word) >= 4 and word not in self._GENERIC_PLACE_WORDS
        ]
        if not expected_words:
            return True

        compact_result = re.sub(r"[^\w]+", "", result_text.casefold())
        return any(
            word in compact_result or compact_result.find(word[: max(4, len(word) - 2)]) >= 0
            for word in expected_words
        )

    def _photon_geocode(
        self,
        query: str,
        country: str,
        expected_name: str | None = None,
    ) -> Optional[dict]:
        search_text = query.strip()
        if country.lower() not in search_text.lower():
            search_text = f"{search_text}, {country}"

        try:
            data = map_http_client.get_json(
                self.PHOTON_BASE_URL,
                params={"q": search_text, "limit": 5, "lang": "en"},
                headers={"User-Agent": "MagicTripPlanner/1.0 academic-project"},
                timeout=12,
                cache_key=f"photon-geocode:{search_text.lower()}",
                min_interval_seconds=1.1,
                context="Photon geocoding",
            )
        except Exception:
            return None

        if not isinstance(data, dict):
            return None

        for feature in data.get("features") or []:
            if not isinstance(feature, dict):
                continue
            properties = feature.get("properties") or {}
            feature_country = str(properties.get("country") or "")
            country_code = str(properties.get("countrycode") or "")
            if country.casefold() == "sri lanka" and not (
                feature_country.casefold() == "sri lanka"
                or country_code.casefold() in {"lk", "lka"}
            ):
                continue

            coordinates = (feature.get("geometry") or {}).get("coordinates") or []
            if len(coordinates) < 2 or not self.valid_coordinate_pair(
                coordinates[1], coordinates[0]
            ):
                continue

            label_parts = [
                properties.get("name"),
                properties.get("city"),
                properties.get("state"),
                properties.get("country"),
            ]
            display_name = ", ".join(
                str(value) for value in label_parts if value
            )
            if expected_name and not self._matches_expected_name(
                expected_name, display_name
            ):
                continue
            return {
                "display_name": display_name,
                "latitude": float(coordinates[1]),
                "longitude": float(coordinates[0]),
                "provider": "photon_openstreetmap",
                "osm_type": properties.get("osm_type"),
                "osm_id": properties.get("osm_id"),
            }

        return None

    def geocode_candidates(
        self,
        queries: Iterable[str],
        country: str = "Sri Lanka",
        *,
        expected_name: str | None = None,
    ) -> Optional[dict]:
        candidates = self._candidate_queries(queries)
        if not candidates:
            return None

        if country.casefold() == "sri lanka":
            for candidate in candidates:
                local_result = lookup_sri_lanka_location(candidate)
                if local_result:
                    return local_result

        # At most one paid Google request is allowed for a logical lookup,
        # even when several free-provider query variants are available.
        if google_maps_service.enabled("geocoding"):
            try:
                google_result = google_maps_service.geocode(candidates[0], country)
                if google_result:
                    return google_result
            except Exception:
                pass
        elif google_maps_service.enabled("places"):
            # Places text search is generally better than address geocoding for
            # attractions. Keep it to one paid request per logical lookup.
            try:
                places = google_maps_service.search_places(candidates[0], limit=1)
                if places:
                    item = places[0]
                    location = item.get("location") or {}
                    if self.valid_coordinate_pair(
                        location.get("latitude"), location.get("longitude")
                    ):
                        return {
                            "display_name": (
                                item.get("formattedAddress")
                                or (item.get("displayName") or {}).get("text")
                                or candidates[0]
                            ),
                            "latitude": float(location["latitude"]),
                            "longitude": float(location["longitude"]),
                            "provider": "google_places",
                            "place_id": item.get("id"),
                        }
            except Exception:
                pass

        for candidate in candidates[: self.MAX_FREE_PROVIDER_ATTEMPTS]:
            result = self._nominatim_geocode(candidate, country)
            if result:
                return result

        # Photon indexes the same open map data differently and frequently
        # resolves canonical POI names that Nominatim's address-oriented search
        # misses. Try the exact label plus the broadest name variants.
        secondary_candidates = [candidates[0], *reversed(candidates[-2:])]
        for candidate in list(dict.fromkeys(secondary_candidates))[
            : self.MAX_SECONDARY_PROVIDER_ATTEMPTS
        ]:
            result = self._photon_geocode(
                candidate, country, expected_name=expected_name
            )
            if result:
                return result

        return None

    def geocode(
        self,
        query: str,
        country: str = "Sri Lanka",
    ) -> Optional[dict]:
        return self.geocode_candidates([query], country)
