import datetime
from functools import cache
import json
import os
from pathlib import Path
from typing import Optional, Any, TypeVar, overload
from logging import getLogger

import platformdirs
from pydantic import BaseModel, ValidationError
import requests


logger = getLogger(__name__)


def get_cache_dir(appname: str, appauthor: Optional[str] = None, version: Optional[str] = None) -> Path:
    """Small method to construct a good cache directory for an application.
    Use platformdirs for more customization."""
    app_dir = platformdirs.site_data_dir(
        appname,
        appauthor=appauthor,
        version=version,
        ensure_exists=True,
    )
    directory = Path(app_dir) / "config_cache"
    return directory


class Confierge:
    """Client for an application to fetch/post configs from ficus, with local caching and validation.

    Examples
    --------
    >>> confierge = Confierge(base_url="http://ficus.test/v1", cache_dir=get_cache_dir("my_app"))
    >>> config_data = confierge.get_config_safe("my_app")
    """

    cache_dir: Path
    base_url: str
    configs_url: str
    scopes_url: str

    def __init__(
        self,
        base_url: Optional[str] = None,
        cache_dir: Optional[Path] = None,
        raise_connection_errors: bool = False,
    ):
        if base_url is None:
            base_url = os.getenv("FICUS_BASE_URL", "http://eng-tools/ficus-dev")
        self.base_url = base_url
        self.configs_url = f"{self.base_url}/v1/configs"
        self.scopes_url = f"{self.base_url}/v1/scopes"

        if cache_dir is None:
            cache_dir = get_cache_dir("confierge")
        self.cache_dir = cache_dir

        # TODO: Make cache file format configurable json/yaml

        try:
            self.test_connection()
        except Exception:
            if raise_connection_errors:
                raise

    def test_connection(self):
        """Test connection to the Ficus server."""
        try:
            response = requests.get(self.base_url)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"Failed to connect to Ficus server at {self.base_url}: {e}")
            raise

    @cache
    def get_ficus_scopes(self) -> set[str]:
        """Get the set of valid scopes from the Ficus server."""
        try:
            response = requests.get(self.scopes_url)
            response.raise_for_status()
            return set(response.json())
        except requests.RequestException as e:
            logger.error(f"Failed to query scopes api: {e}")
            raise

    def validate_scopes(self, scopes: set[str]):
        ficus_scopes = self.get_ficus_scopes()
        if not scopes.issubset(ficus_scopes):
            raise ValueError(f"Invalid scopes: {scopes - ficus_scopes}")

    def _cache_file_path(
        self,
        namespace: str,
        mode: Optional[str],
        scopes: Optional[dict[str, str]],
    ) -> Path:
        scope_part = "_".join(f"{k}-{v}" for k, v in sorted((scopes or {}).items()))
        mode_part = f"{mode}" if mode else ""
        return self.cache_dir / f"{namespace}_{scope_part}_{mode_part}.json"

    def _expire_cache(self, cache_file: Path):
        """Expire cache file and backdate with timestamp."""
        if cache_file.exists():
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            cache_file.rename(cache_file.with_name(f"{timestamp}_{cache_file.name}"))

    def _get_cache(
        self,
        namespace: str,
        mode: Optional[str],
        scopes: Optional[dict[str, str]],
    ) -> dict[str, Any] | None:
        """Generate cache file path based on namespace, identifiers, and mode."""
        cache_file = self._cache_file_path(namespace, mode, scopes)
        cached_data = cache_file.read_text() if cache_file and cache_file.exists() else None

        if cached_data is None:
            logger.info(f"No cache file found at {cache_file}")
            return None

        return json.loads(cached_data)

    def _save_cache(
        self,
        namespace: str,
        mode: Optional[str],
        scopes: Optional[dict[str, str]],
        data: dict[str, Any],
    ):
        """Save data to cache file. If file exists, expire old cache. If data the same, skip."""
        curr = self._get_cache(namespace, mode, scopes)
        if curr == data:
            logger.info("New data is identical to cached data, skipping cache save.")
            return

        cache_file = self._cache_file_path(namespace, mode, scopes)

        if cache_file.exists():
            self._expire_cache(cache_file)

        cache_file.write_text(json.dumps(data, indent=2))

    def get_config(
        self,
        namespace: str,
        mode: Optional[str] = None,
        scopes: Optional[dict[str, str]] = None,
    ):
        """Get config data complete with merged defaults and scope overrides."""

        url = f"{self.configs_url}/{namespace}"
        params = {"mode": mode} if mode else {}

        if scopes:
            self.validate_scopes(set(scopes.keys()))
            params.update(scopes)
        response = requests.get(url, params=params)
        response.raise_for_status()
        # TODO: Use models from ficus
        return response.json()["config"]["data"]

    T = TypeVar("T", bound=BaseModel)

    @overload
    def get_config_safe(
        self,
        namespace: str,
        mode: str | None = None,
        scopes: dict[str, str] | None = None,
        model: type[T] = ...,
    ) -> T: ...

    @overload
    def get_config_safe(
        self,
        namespace: str,
        mode: str | None = None,
        scopes: dict[str, str] | None = None,
        model: None = None,
    ) -> dict[str, Any]: ...

    def get_config_safe(
        self,
        namespace: str,
        mode: str | None = None,
        scopes: dict[str, str] | None = None,
        model: type[T] | None = None,
    ) -> T | dict[str, Any]:
        """Get (and cache) config data and merged scope overrides, falling back to cached data if errors."""

        try:
            data = self.get_config(namespace, mode, scopes)
        except requests.RequestException:
            cache_file = self._cache_file_path(namespace, mode, scopes)
            cached_data = self._get_cache(namespace, mode, scopes)

            if cached_data is not None:
                data = cached_data
                logger.warning(
                    f"Error fetching config, using cached config from {cache_file}",
                    exc_info=True,
                )
            else:
                raise

        # validate the data
        if model is not None:
            try:
                config = model.model_validate(data)
            except ValidationError:
                # TODO: save the invalid data to a separate file for debugging
                cache_file = self._cache_file_path(namespace, mode, scopes)
                cached_data = self._get_cache(namespace, mode, scopes)
                if cached_data is not None:
                    config = model.model_validate(json.loads(cached_data))
                    logger.warning(
                        f"Could not validate new data, using cached config from {cache_file}",
                        exc_info=True,
                    )
                else:
                    raise
        else:
            config = data

        # Cache the new config
        self._save_cache(namespace, mode, scopes, data=data)

        return config

    def post_config_file(
        self,
        namespace: str,
        config_data: dict,
        mode: Optional[str] = None,
        scopes: Optional[dict[str, str]] = None,
    ):
        """Post config data to save to the database"""
        url = f"{self.configs_url}/{namespace}"
        params = {"mode": mode} if mode else {}

        if scopes:
            self.validate_scopes(set(scopes.keys()))
            params.update(scopes)

        response = requests.post(
            url,
            json=config_data,
            params=params,
        )
        response.raise_for_status()
        # TODO: Cache failed posts and figure out how to rectify such a situation

    # TODO: Add Update/Delete
