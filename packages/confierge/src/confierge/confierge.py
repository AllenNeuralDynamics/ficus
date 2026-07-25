import datetime
import json
import os
from pathlib import Path
from typing import Optional, Any, TypeVar, overload
from logging import getLogger

from pydantic import BaseModel, ValidationError
import requests


logger = getLogger(__name__)


class Confierge:
    """Client for an application to fetch/post configs from ficus, with local caching and validation."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        scopes: set[str] | None = {"hostname", "subject_id"},
    ):
        if base_url is None:
            base_url = os.getenv("FICUS_BASE_URL", "http://eng-tools/ficus-dev/v1/configs")
        self.base_url = base_url

        self.scopes = scopes

        # TODO: Make cache file format configurable json/yaml

    def _validate_scopes(self):
        url = self.base_url + "/scopes"
        try:
            response = requests.get(url)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"Failed to query api scopes: {e}")
            raise
        if not self.scopes.issubset(response.json()):
            raise ValueError(f"Invalid scopes: {self.scopes - set(response.json())}")

    def _cache_file_name(
        self,
        namespace: str,
        mode: Optional[str],
        scopes: Optional[dict[str, str]],
    ) -> str:
        scope_part = "_".join(f"{k}-{v}" for k, v in sorted((scopes or {}).items()))
        mode_part = f"{mode}" if mode else ""
        return f"{namespace}_{scope_part}_{mode_part}.json"

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
        cache_dir: Path,
    ) -> dict[str, Any] | None:
        """Generate cache file path based on namespace, identifiers, and mode."""
        cache_file_name = self._cache_file_name(namespace, mode, scopes)

        cache_file = cache_dir / cache_file_name
        cached_data = cache_file.read_text() if cache_file.exists() else None

        if cached_data is None:
            logger.info(f"No cache file found at {cache_file}")
            return None

        return json.loads(cached_data)

    def _save_cache(
        self,
        namespace: str,
        mode: Optional[str],
        scopes: Optional[dict[str, str]],
        cache_dir: Path,
        data: dict[str, Any],
    ):
        """Save data to cache file. If file exists, expire old cache. If data the same, skip."""
        curr = self._get_cache(namespace, mode, scopes, cache_dir=cache_dir)
        if curr == data:
            logger.info("New data is identical to cached data, skipping cache save.")
            return

        cache_file_name = self._cache_file_name(namespace, mode, scopes)
        cache_file = cache_dir / cache_file_name

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

        url = f"{self.base_url}/configs/{namespace}"
        params = {"mode": mode} if mode else {}

        if scopes:
            if not set(scopes.keys()).issubset(self.scopes):
                raise ValueError(f"Invalid scopes: {set(scopes.keys()) - self.scopes}")
            params.update(scopes)
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()['config']['data']

    T = TypeVar("T", bound=BaseModel)

    @overload
    def get_config_safe(
        self,
        namespace: str,
        cache_dir: Optional[Path],
        mode: str | None = None,
        scopes: dict[str, str] | None = None,
        model: type[T] = ...,
    ) -> T: ...

    @overload
    def get_config_safe(
        self,
        namespace: str,
        cache_dir: Optional[Path],
        mode: str | None = None,
        scopes: dict[str, str] | None = None,
        model: None = None,
    ) -> dict[str, Any]: ...

    def get_config_safe(
        self,
        namespace: str,
        cache_dir: Optional[Path],
        mode: str | None = None,
        scopes: dict[str, str] | None = None,
        model: type[T] | None = None,
    ) -> T | dict[str, Any]:
        """Get (and cache) config data and merged scope overrides, falling back to cached data if errors."""

        try:
            data = self.get_config(namespace, mode, scopes)
        except requests.RequestException as e:
            cache_file = cache_dir / self._cache_file_name(namespace, mode, scopes) if cache_dir else None
            cached_data = self._get_cache(namespace, mode, scopes, cache_dir=cache_dir)

            if cached_data is not None:
                data = cached_data
                logger.warning(
                    f"Error fetching config, using cached config from {cache_file}",
                    exc_info=True,
                )
            else:
                raise e

        # validate the data
        if model is not None:
            try:
                config = model.model_validate(data)
            except ValidationError as e:
                # TODO: save the invalid data to a separate file for debugging
                if cached_data is not None:
                    config = model.model_validate(json.loads(cached_data))
                    logger.warning(
                        f"Could not validate new data, using cached config from {cache_file}",
                        exc_info=True,
                    )
                else:
                    raise e
        else:
            config = data

        # Cache the new config
        if cache_dir is not None:
            self._save_cache(namespace, mode, scopes, cache_dir=cache_dir, data=data)

        return config

    def post_config_file(
        self,
        namespace: str,
        config_data: dict,
        mode: Optional[str] = None,
        scopes: Optional[dict[str, str]] = None,
    ):
        """Post config data to save to the database"""
        url = f"{self.base_url}/configs/{namespace}"
        params = {"mode": mode} if mode else {}

        if scopes:
            if not set(scopes.keys()).issubset(self.scopes):
                raise ValueError(f"Invalid scopes: {set(scopes.keys()) - self.scopes}")
            params.update(scopes)

        response = requests.post(
            url,
            json=config_data,
            params=params,
        )
        response.raise_for_status()

    # TODO: Add Update/Delete