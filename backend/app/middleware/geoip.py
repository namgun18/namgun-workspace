"""GeoIP stub — workspace edition (no GeoIP DB bundled)."""

import logging

logger = logging.getLogger(__name__)


def lookup_country(ip: str) -> tuple[str | None, str | None]:
    """Returns (country_code, country_name). Always None in workspace base."""
    return None, None
