import re
from urllib.parse import quote

from app.services.map_http import map_http_client


class MediaLookupService:
    SEARCH_URL = "https://en.wikipedia.org/w/api.php"
    COMMONS_SEARCH_URL = "https://commons.wikimedia.org/w/api.php"
    SUMMARY_URL_TEMPLATE = "https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
    USER_AGENT = "MagicTripPlanner/1.0 academic-project"

    def lookup_media(self, query: str | None) -> dict[str, str | None]:
        if not query:
            return {
                "image_url": None,
                "description": None,
            }

        normalized_query = " ".join(query.split())

        if not normalized_query:
            return {
                "image_url": None,
                "description": None,
            }

        for candidate_query in self._query_variants(normalized_query):
            try:
                title = self._search_title(candidate_query)

                if not title:
                    continue

                if not self._is_relevant_title(candidate_query, title):
                    image_url = self._search_commons_image(candidate_query)

                    if image_url:
                        return {
                            "image_url": image_url,
                            "description": None,
                        }

                    continue

                summary = map_http_client.get_json(
                    self.SUMMARY_URL_TEMPLATE.format(title=quote(title, safe="")),
                    headers={"User-Agent": self.USER_AGENT},
                    timeout=15,
                    cache_key=f"wiki-summary:{title.lower()}",
                    min_interval_seconds=0.2,
                    context="Wikipedia summary lookup",
                )

            except Exception:
                continue

            image = summary.get("originalimage") or summary.get("thumbnail") or {}
            description = summary.get("extract") or summary.get("description")
            image_url = image.get("source")

            if not image_url:
                image_url = self._search_commons_image(candidate_query)

            if image_url or description:
                return {
                    "image_url": image_url,
                    "description": self._trim_description(description),
                }

        image_url = self._search_commons_image(normalized_query)

        return {
            "image_url": image_url,
            "description": None,
        }

    def _query_variants(self, query: str) -> list[str]:
        variants = [query]

        before_comma = query.split(",", 1)[0].strip()

        if before_comma:
            variants.append(before_comma)

        without_sri_lanka = re.sub(
            r"\bSri\s+Lanka\b",
            "",
            query,
            flags=re.IGNORECASE,
        )
        without_sri_lanka = re.sub(r"\s+", " ", without_sri_lanka).strip(" ,")

        if without_sri_lanka:
            variants.append(without_sri_lanka)

        unique_variants = []

        for variant in variants:
            cleaned_variant = " ".join(variant.split())

            if cleaned_variant and cleaned_variant not in unique_variants:
                unique_variants.append(cleaned_variant)

        return unique_variants

    def _search_title(self, query: str) -> str | None:
        results = map_http_client.get_json(
            self.SEARCH_URL,
            params={
                "action": "query",
                "format": "json",
                "list": "search",
                "srsearch": query,
                "srlimit": 1,
                "srprop": "",
            },
            headers={"User-Agent": self.USER_AGENT},
            timeout=15,
            cache_key=f"wiki-search:{query.lower()}",
            min_interval_seconds=0.2,
            context="Wikipedia title search",
        )

        search_results = (results.get("query") or {}).get("search") or []

        if not search_results:
            return None

        return search_results[0].get("title")

    def _significant_tokens(self, text: str) -> set[str]:
        stop_words = {
            "sri",
            "lanka",
            "hotel",
            "resort",
            "guest",
            "house",
            "accommodation",
            "the",
            "and",
            "road",
            "district",
            "province",
        }

        return {
            token
            for token in re.findall(r"[a-z0-9]+", text.lower())
            if len(token) > 2 and token not in stop_words
        }

    def _is_relevant_title(self, query: str, title: str) -> bool:
        query_tokens = self._significant_tokens(query)
        title_tokens = self._significant_tokens(title)

        if not query_tokens or not title_tokens:
            return False

        return bool(query_tokens & title_tokens)

    def _search_commons_image(self, query: str) -> str | None:
        try:
            results = map_http_client.get_json(
                self.COMMONS_SEARCH_URL,
                params={
                    "action": "query",
                    "format": "json",
                    "generator": "search",
                    "gsrsearch": query,
                    "gsrnamespace": 6,
                    "gsrlimit": 3,
                    "prop": "imageinfo",
                    "iiprop": "url|mime",
                },
                headers={"User-Agent": self.USER_AGENT},
                timeout=15,
                cache_key=f"commons-image:{query.lower()}",
                min_interval_seconds=0.2,
                context="Wikimedia Commons image lookup",
            )

        except Exception:
            return None

        pages = (results.get("query") or {}).get("pages") or {}

        for page in pages.values():
            image_infos = page.get("imageinfo") or []

            if not image_infos:
                continue

            image_info = image_infos[0]
            mime_type = image_info.get("mime") or ""
            image_url = image_info.get("url")

            if image_url and mime_type.startswith("image/"):
                return image_url

        return None

    def _trim_description(self, text: str | None, max_length: int = 180) -> str | None:
        if not text:
            return None

        cleaned = re.sub(r"\s+", " ", text).strip()

        if len(cleaned) <= max_length:
            return cleaned

        shortened = cleaned[: max_length - 3].rsplit(" ", 1)[0].strip()

        if not shortened:
            return cleaned[: max_length - 3].strip() + "..."

        return shortened + "..."
