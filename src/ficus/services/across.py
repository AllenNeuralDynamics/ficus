"""Compare resolved config fields across the identifiers of one scope.

For each identifier (each rig under ``hostname``, say), resolve the config the way that identifier
sees it (defaults merged with its own leaf) and report, per requested field, the resolved value
and the leaf that set it.
"""

from typing import Any

from typing_extensions import Sentinel

from ficus.core.exceptions import (
    ConfigDecodeError,
    InvalidNamespaceError,
    UnsupportedFileTypeError,
)
from ficus.database.data_store import DataStore
from ficus.schemas.configs import AcrossConfigItem, Leaf, LeafRef
from ficus.services.configs import get_config
from ficus.services.discovery import list_namespaces, list_scope_identifiers


_MISSING = Sentinel("_MISSING")


def _field(data: dict, name: str) -> Any | _MISSING:
    """The value at dotted path ``name`` (``camera.frame_rate``), or ``_MISSING`` if absent."""
    value = data
    for part in name.split("."):
        if not isinstance(value, dict) or part not in value:
            return _MISSING
        value = value[part]
    return value


def _field_names(data: dict, prefix: str = "") -> list[str]:
    """Dotted paths of every leaf value in ``data`` (an empty dict counts as a leaf value)."""
    names = []
    for key, value in data.items():
        name = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict) and value:
            names.extend(_field_names(value, name))
        else:
            names.append(name)
    return names


def _source(leaves: list[Leaf], name: str) -> LeafRef | None:
    """The highest leaf that sets anything at ``name``; it wins the merge for that path."""
    for leaf in reversed(leaves):
        if _field(leaf.data, name) is not _MISSING:
            return LeafRef(**leaf.model_dump(exclude={"data"}))
    return None


def _identifiers(
    data_store: DataStore, scope: str, namespace: str, identifiers: list[str] | None
) -> list[str]:
    """The given identifiers (deduplicated, in order), or every identifier of ``scope`` that has
    a leaf for ``namespace``."""
    if identifiers is None:
        return list_scope_identifiers(data_store, scope, namespace=namespace)
    if scope not in data_store.scopes:
        raise ValueError(f"Unknown scope: {scope}")
    return list(dict.fromkeys(identifiers))


def resolve_across(
    data_store: DataStore,
    namespace: str,
    scope: str,
    mode: str,
    fields: list[str] | None,
    identifiers: list[str] | None = None,
) -> list[AcrossConfigItem]:
    """Resolve ``fields`` for identifiers of ``scope``.

    Parameters:
    -----------
        namespace: str
            The namespace whose config is resolved.
        scope: str
            The scope to compare across (its identifiers are the rows).
        mode: str
            The config mode to resolve.
        fields: list[str] | None
            Dotted field paths to report. None reports every leaf field of each resolved config.
        identifiers: list[str] | None
            Only these identifiers, in this order. None means every identifier of ``scope`` that
            has a leaf for ``namespace``. An identifier with no folder resolves to the lower
            leaves (a new rig shows its defaults).

    Returns:
    --------
        list[AcrossConfigItem]
            One item per identifier. ``values[field]`` is the resolved value and
            ``sources[field]`` the leaf that set it; both are None when the field is absent.
            When a field resolves to a non-empty object, ``sources`` also has an entry for every
            field below it, so each one names the leaf that set it.
            An identifier whose leaves can't be read has ``error`` set and empty values/sources,
            so one broken rig doesn't hide the rest.

    Raises:
    -------
        InvalidNamespaceError
            if ``namespace`` has no defaults.
        ValueError
            if ``scope`` is unknown.
    """
    if namespace not in list_namespaces(data_store):
        raise InvalidNamespaceError(f"Namespace not found in defaults: {namespace}")
    items = []
    for identifier in _identifiers(data_store, scope, namespace, identifiers):
        try:
            config = get_config(
                data_store,
                namespace,
                mode=mode,
                scope_identifiers={scope: identifier},
                include_leaves=True,
            )
        except (ConfigDecodeError, UnsupportedFileTypeError) as error:
            items.append(
                AcrossConfigItem(identifier=identifier, values={}, sources={}, error=str(error))
            )
            continue
        names = fields if fields is not None else _field_names(config.data)
        values = {}
        sources = {}
        for name in names:
            value = _field(config.data, name)
            values[name] = None if value is _MISSING else value
            sources[name] = None if value is _MISSING else _source(config.leaves, name)
            if isinstance(value, dict) and value:
                for sub in _field_names(value, name):
                    sources.setdefault(sub, _source(config.leaves, sub))
        items.append(AcrossConfigItem(identifier=identifier, values=values, sources=sources))
    return items
