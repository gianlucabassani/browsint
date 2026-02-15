"""
Async WebFetcher implementation using httpx.

This module provides an asynchronous web fetching implementation that addresses
the following issues from the synchronous version:

1. Non-blocking I/O: Uses httpx for async HTTP requests
2. Simplified retry logic: Single retry implementation (no nested loops)
3. Async cache I/O: Uses aiofiles for non-blocking file operations
4. Async politeness delays: Uses asyncio.sleep() instead of time.sleep()
"""

import asyncio
import hashlib
import logging
import random
from pathlib import Path
from typing import NamedTuple, Optional

import httpx
import aiofiles
import aiofiles.os

logger = logging.getLogger("scraper.fetcher")


class FetchResponse(NamedTuple):
    """
    Represents a complete response from an HTTP request.
    
    Attributes:
        status_code: HTTP status code of the response
        content: Response content as bytes, None if unavailable
        headers: Response headers (httpx.Headers)
        url: URL of the request (may differ from original due to redirects)
        encoding: Content encoding, None if not specified
    """
    status_code: int
    content: bytes | None
    headers: httpx.Headers
    url: str
    encoding: str | None


class WebFetcher:
    """
    Asynchronous web content fetcher with error handling, retry logic, and politeness.
    
    Features:
    - Async HTTP requests using httpx
    - Async file-based caching with aiofiles
    - Rate limiting with async delays
    - Configurable retry logic with exponential backoff
    - User-agent customization
    
    Args:
        cache_dir: Directory for page cache (None to disable caching)
        user_agent: Custom User-Agent string identifying the crawler
        delay_range: Tuple of (min, max) wait time between requests in seconds
        timeout: Default timeout for HTTP requests in seconds
        max_retries: Maximum number of retry attempts for failed requests
    """

    def __init__(
        self,
        cache_dir: str | None = None,
        user_agent: str | None = None,
        delay_range: tuple[float, float] = (1.0, 3.0),
        timeout: float = 30.0,
        max_retries: int = 3,
    ):
        self.headers = {
            "User-Agent": user_agent or "Browsint/1.0 Research Bot",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

        self.delay_range = delay_range
        self.timeout = timeout
        self.max_retries = max_retries
        self.last_request_time: float = 0.0
        self._request_lock = asyncio.Lock()  # Ensure politeness across concurrent requests

        # Cache configuration
        self.cache_enabled = cache_dir is not None
        if self.cache_enabled:
            self.cache_dir = Path(cache_dir)
            # Create cache directory synchronously at init (one-time operation)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Cache enabled at {self.cache_dir}")

        # HTTP client (will be initialized lazily)
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """Context manager entry - initialize HTTP client."""
        await self._ensure_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup HTTP client."""
        await self.close()

    async def _ensure_client(self):
        """Lazily initialize the HTTP client if not already created."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                follow_redirects=True,
                headers=self.headers,
                limits=httpx.Limits(max_keepalive_connections=20, max_connections=100)
            )

    async def close(self):
        """Close the HTTP client and release resources."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _get_cache_path(self, url: str) -> Path:
        """
        Generate a unique file path for the URL in the cache.
        
        Args:
            url: The URL to generate cache path for
            
        Returns:
            Complete cache file path
        """
        url_hash = hashlib.md5(url.encode()).hexdigest()
        return self.cache_dir / f"{url_hash}.html"

    async def _check_cache(self, url: str) -> str | None:
        """
        Check if the URL is cached and return the text content.
        
        Uses aiofiles for non-blocking file I/O.
        
        Args:
            url: The URL to look up in cache
            
        Returns:
            Page content if present in cache, None otherwise
        """
        if not self.cache_enabled:
            return None

        cache_path = self._get_cache_path(url)
        
        # Check if file exists (async)
        try:
            if await aiofiles.os.path.exists(cache_path):
                logger.debug(f"Cache hit for {url}")
                async with aiofiles.open(cache_path, encoding="utf-8") as f:
                    return await f.read()
        except Exception as e:
            logger.warning(f"Error reading cache for {url}: {e}")

        return None

    async def _save_to_cache(self, url: str, content: str) -> bool:
        """
        Save text content to cache asynchronously.
        
        Args:
            url: The URL associated with the content
            content: The HTML content to save
            
        Returns:
            True if save was successful, False otherwise
        """
        if not self.cache_enabled:
            return False

        try:
            cache_path = self._get_cache_path(url)
            async with aiofiles.open(cache_path, "w", encoding="utf-8") as f:
                await f.write(content)
            return True
        except Exception as e:
            logger.warning(f"Unable to save to cache {url}: {e}")
            return False

    async def _respect_politeness(self) -> None:
        """
        Wait to respect politeness policies (delay between requests).
        
        Uses async lock to ensure thread-safe rate limiting and asyncio.sleep()
        for non-blocking delays.
        """
        async with self._request_lock:
            current_time = asyncio.get_event_loop().time()
            elapsed = current_time - self.last_request_time

            min_delay = self.delay_range[0]
            if elapsed < min_delay:
                sleep_time = min_delay - elapsed
                logger.debug(f"Waiting {sleep_time:.2f}s for politeness")
                await asyncio.sleep(sleep_time)

            self.last_request_time = asyncio.get_event_loop().time()

    async def fetch(
        self,
        url: str,
        force_download: bool = False,
        timeout: float | None = None,
        retries: int | None = None
    ) -> str | None:
        """
        Fetch the text content of a URL with caching, timeout, and retry options.
        
        Args:
            url: The URL to download
            force_download: Force download even if present in cache
            timeout: Request timeout in seconds (overrides default)
            retries: Number of retry attempts (overrides default)
            
        Returns:
            Text content of the page or None on failure
        """
        response_obj = await self.fetch_full_response(url, force_download, timeout, retries)
        
        if response_obj and response_obj.content:
            try:
                encoding = response_obj.encoding or 'utf-8'
                return response_obj.content.decode(encoding, errors='replace')
            except Exception as e:
                logger.warning(f"Error decoding text content for {url}: {e}")
                return None
        return None

    async def fetch_full_response(
        self,
        url: str,
        force_download: bool = False,
        timeout: float | None = None,
        retries: int | None = None
    ) -> FetchResponse | None:
        """
        Fetch complete response (status, content, headers, etc.) for a URL.
        
        Implements:
        - Cache checking (unless force_download is True)
        - Politeness delays
        - Retry logic with exponential backoff
        - Comprehensive error handling
        
        Args:
            url: The URL to download
            force_download: Force download (ignore cache)
            timeout: Request timeout in seconds (overrides default)
            retries: Number of retry attempts (overrides default)
            
        Returns:
            FetchResponse object containing response data, or None on failure
        """
        # Check cache first (unless forcing download)
        if not force_download:
            cached_content = await self._check_cache(url)
            if cached_content is not None:
                # Return a "synthetic" response from cache
                return FetchResponse(
                    status_code=200,
                    content=cached_content.encode('utf-8'),
                    headers=httpx.Headers({'content-type': 'text/html; charset=utf-8'}),
                    url=url,
                    encoding='utf-8'
                )

        # Ensure client is initialized
        await self._ensure_client()

        # Respect politeness delay
        await self._respect_politeness()

        # Use provided values or defaults
        actual_timeout = timeout if timeout is not None else self.timeout
        actual_retries = retries if retries is not None else self.max_retries

        # Retry loop with exponential backoff
        attempt = 0
        while attempt < actual_retries:
            try:
                logger.info(f"Downloading {url} (attempt {attempt + 1}/{actual_retries})")
                
                response = await self._client.get(
                    url,
                    timeout=actual_timeout
                )

                # Check for HTTP errors (4xx, 5xx)
                response.raise_for_status()

                content_bytes = response.content
                
                # Detect encoding
                encoding = response.encoding
                if not encoding:
                    # Try to detect from content
                    try:
                        import charset_normalizer
                        detected = charset_normalizer.from_bytes(content_bytes[:10000]).best()
                        encoding = detected.encoding if detected else 'utf-8'
                    except:
                        encoding = 'utf-8'

                # Save to cache if enabled
                if self.cache_enabled and response.status_code == 200:
                    try:
                        text_content = content_bytes.decode(encoding, errors='replace')
                        await self._save_to_cache(url, text_content)
                    except Exception as e:
                        logger.warning(f"Failed to cache {url}: {e}")

                return FetchResponse(
                    status_code=response.status_code,
                    content=content_bytes,
                    headers=response.headers,
                    url=str(response.url),
                    encoding=encoding
                )

            except httpx.TimeoutException as e:
                logger.warning(f"Timeout downloading {url}: {e}")
            except httpx.HTTPStatusError as e:
                logger.warning(f"HTTP error {e.response.status_code} for {url}")
                # Don't retry on 4xx client errors (except 429)
                if 400 <= e.response.status_code < 500 and e.response.status_code != 429:
                    logger.error(f"Client error {e.response.status_code} for {url}, not retrying")
                    return None
            except httpx.RequestError as e:
                logger.warning(f"Request error downloading {url}: {e}")
            except Exception as e:
                logger.warning(f"Unexpected error downloading {url}: {e}")

            attempt += 1
            if attempt < actual_retries:
                # Exponential backoff with jitter
                sleep_time = random.uniform(2, 5) * (2 ** (attempt - 1))
                logger.debug(f"Waiting {sleep_time:.2f} seconds before retry")
                await asyncio.sleep(sleep_time)

        logger.error(f"Failed to download {url} after {actual_retries} attempts")
        return None

    async def clear_cache(self) -> None:
        """Clear all cached files asynchronously."""
        if not self.cache_enabled:
            logger.info("Cache not enabled, nothing to clear")
            return

        try:
            cache_files = list(self.cache_dir.glob("*.html"))
            for cache_file in cache_files:
                await aiofiles.os.remove(cache_file)
            logger.info(f"Cleared {len(cache_files)} files from cache")
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")


# Convenience function for backward compatibility and simple usage
async def fetch_url(url: str, **kwargs) -> str | None:
    """
    Convenience function to fetch a single URL asynchronously.
    
    This creates a temporary AsyncWebFetcher, fetches the URL, and cleans up.
    For multiple requests, create an AsyncWebFetcher instance and reuse it.
    
    Args:
        url: The URL to fetch
        **kwargs: Additional arguments passed to AsyncWebFetcher constructor
        
    Returns:
        Text content of the URL or None on failure
    """
    async with AsyncWebFetcher(**kwargs) as fetcher:
        return await fetcher.fetch(url)

