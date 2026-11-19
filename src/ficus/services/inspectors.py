"""Inspect where config fields are declared, and compare resolved configs.

A *declaration* is one leaf setting a field. Fields are glom paths, such as ``camera.frame_rate``.
The functions that take a ``ConfigObject`` need it resolved with ``include_leaves=True``.
"""

from typing import Any

import glom

from ficus.core.exceptions import (
    ConfigDecodeError,
    InvalidNamespaceError,
    UnsupportedFileTypeError,
)
from ficus.database.data_store import DataStore
from ficus.schemas.configs import (
    AcrossConfigItem,
    ConfigErrorResponse,
    ConfigObject,
    FieldDeclaration,
    Leaf,
    LeafRef,
)
from ficus.services.configs import get_config
from ficus.services.discovery import list_namespaces, list_scope_identifiers
from ficus.services.utils import DEFAULT_MODE
from ficus.utils.dict_merge import _deep_update, deep_diff, flatten_recursive_dict


def _leaves(config: ConfigObject) -> list[Leaf]:
    if config.leaves is None:
        raise ValueError("Config has no leaves; resolve it with include_leaves=True.")
    return config.leaves


def _lookup(data: dict, field: str) -> tuple[bool, Any]:
    """``(True, value)`` if ``field`` is in ``data``, else ``(False, None)``."""
    try:
        return True, glom.glom(data, field)
    except glom.PathAccessError:
        return False, None


def _ref(leaf: Leaf) -> LeafRef:
    return LeafRef(**leaf.model_dump(exclude={"data"}))


def get_all_field_declarations(config: ConfigObject, field: str) -> list[FieldDeclaration]:
    """Return every declaration of a field in the config's leaf stack, lowest-rank first.

    Each declaration's value is what that leaf sets: for an object, only the keys that leaf has.
    """
    declarations: list[FieldDeclaration] = []
    for leaf in _leaves(config):
        found, value = _lookup(leaf.data, field)
        if found:
            declarations.append(FieldDeclaration(field=field, value=value, source_leaf=_ref(leaf)))
    return declarations


def get_active_field_declaration(config: ConfigObject, field: str) -> FieldDeclaration | None:
    """Return the highest-rank declaration of a field, the one that ends up in the config.

    None if the field isn't in the resolved config, including when a higher leaf replaced one
    of its parents with a non-object value.
    """
    if not _lookup(config.data, field)[0]:
        return None
    declarations = get_all_field_declarations(config, field)
    return declarations[-1] if declarations else None


def find_redundant_declarations(
    config: ConfigObject, field: str
) -> tuple[list[FieldDeclaration], list[FieldDeclaration]]:
    """Split the declarations above the first one into ``(redundant, overrides)``.

    A declaration is redundant when merging its leaf leaves the field's resolved value unchanged,
    comparing merged values, so an object that repeats only some inherited keys counts as
    redundant. The first declaration sets the field and is in neither list.
    """
    redundancies: list[FieldDeclaration] = []
    overrides: list[FieldDeclaration] = []
    merged: dict = {}
    for leaf in _leaves(config):
        declared, value = _lookup(leaf.data, field)
        had_field, before = _lookup(merged, field)
        merged = _deep_update(merged, leaf.data)
        if not declared:
            continue
        declaration = FieldDeclaration(field=field, value=value, source_leaf=_ref(leaf))
        if not had_field:
            continue
        _, after = _lookup(merged, field)
        (redundancies if after == before else overrides).append(declaration)
    return redundancies, overrides


def find_declarations_in_scope(
    config: ConfigObject, field: str, scope: str | None, mode: str = DEFAULT_MODE
) -> list[FieldDeclaration]:
    """Return the declarations of a field made by leaves of one scope and mode (None = defaults)."""
    return [
        declaration
        for declaration in get_all_field_declarations(config, field)
        if declaration.source_leaf.mode == mode and declaration.source_leaf.scope == scope
    ]


def get_configs_across_scope(
    data_store: DataStore,
    namespace: str,
    scope: str,
    mode: str,
    identifiers: list[str] | None = None,
) -> dict[str, ConfigObject | ConfigErrorResponse]:
    """Resolve the config of each identifier of a scope, or the error that prevented it.

    ``identifiers`` limits the result to those identifiers, in that order; an identifier with no
    folder resolves to the lower leaves (a new rig gets its defaults). Without it, every
    identifier that has a leaf for ``namespace`` is resolved.

    Raises:
    -------
        InvalidNamespaceError
            if ``namespace`` has no defaults.
        ValueError
            if ``scope`` is unknown.
    """
    if namespace not in list_namespaces(data_store):
        raise InvalidNamespaceError(f"Namespace not found in defaults: {namespace}")
    if identifiers is None:
        identifiers = list_scope_identifiers(data_store, scope, namespace=namespace)
    elif scope not in data_store.scopes:
        raise ValueError(f"Unknown scope: {scope}")
    configs: dict[str, ConfigObject | ConfigErrorResponse] = {}
    for identifier in dict.fromkeys(identifiers):
        try:
            configs[identifier] = get_config(
                data_store,
                namespace,
                mode=mode,
                scope_identifiers={scope: identifier},
                include_leaves=True,
            )
        except (ConfigDecodeError, UnsupportedFileTypeError) as error:
            configs[identifier] = ConfigErrorResponse(details=str(error))
    return configs


def _source(config: ConfigObject, field: str) -> LeafRef | None:
    active = get_active_field_declaration(config, field)
    return active.source_leaf if active else None


def resolve_across(
    data_store: DataStore,
    namespace: str,
    scope: str,
    mode: str,
    fields: list[str] | None,
    identifiers: list[str] | None = None,
) -> list[AcrossConfigItem]:
    """Resolve ``fields`` for identifiers of ``scope``: each one's values and their sources.

    ``values[field]`` comes from the resolved config, so an object holds every key the identifier
    gets, whichever leaves set them. ``sources[field]`` is the leaf of the active declaration;
    when a field resolves to a non-empty object, ``sources`` also has an entry for every field
    below it. Both are None when the field is absent. ``fields=None`` reports every field of each
    resolved config. An identifier whose leaves can't be read has ``error`` set.
    """
    items = []
    configs = get_configs_across_scope(data_store, namespace, scope, mode, identifiers)
    for identifier, config in configs.items():
        if isinstance(config, ConfigErrorResponse):
            items.append(
                AcrossConfigItem(identifier=identifier, values={}, sources={}, error=config.details)
            )
            continue
        names = fields if fields is not None else list(flatten_recursive_dict(config.data))
        values: dict[str, Any] = {}
        sources: dict[str, LeafRef | None] = {}
        for name in names:
            found, value = _lookup(config.data, name)
            values[name] = value
            sources[name] = _source(config, name) if found else None
            if found and isinstance(value, dict) and value:
                for sub in flatten_recursive_dict(value, key_prefix=name):
                    sources.setdefault(sub, _source(config, sub))
        items.append(AcrossConfigItem(identifier=identifier, values=values, sources=sources))
    return items


def compare_configs(
    config_1: ConfigObject, config_2: ConfigObject
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Compare two resolved configs: ``(same, different, removed)``, as in ``deep_diff``."""
    return deep_diff(config_1.data, config_2.data)
