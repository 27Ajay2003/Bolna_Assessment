import logging
import aiohttp

logger = logging.getLogger(__name__)

HEADERS = {
    "Accept": "application/json",
    "User-Agent": "StatusWatcher/1.0",
}


async def fetch_incidents(session: aiohttp.ClientSession, url: str) -> list | None:
    """
    Fetch the incidents JSON from a Statuspage.io endpoint.
    Returns a list of incident dicts, or None on failure.
    """
    try:
        async with session.get(url, headers=HEADERS) as response:
            if response.status != 200:
                logger.warning(f"Non-200 response from {url}: {response.status}")
                return None

            data = await response.json(content_type=None)
            return data.get("incidents", [])

    except aiohttp.ClientConnectorError:
        logger.error(f"Connection error fetching {url}")
    except aiohttp.ServerTimeoutError:
        logger.error(f"Timeout fetching {url}")
    except Exception as e:
        logger.error(f"Failed to fetch {url}: {e}")

    return None