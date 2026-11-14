from ficus.database.data_store import DataStore
from ficus.schemas.configs import AcrossConfigItem
from ficus.services.configs import get_config
from ficus.services.discovery import list_scope_identifiers


_MISSING = object()


def _field(data: dict, name: str):
    value = data
    for part in name.split("."):
        if not isinstance(value, dict) or part not in value:
            return _MISSING
        value = value[part]
    return value


def _field_names(data: dict, prefix: str = "") -> list[str]:
    names = []
    for key, value in data.items():
        name = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict) and value:
            names.extend(_field_names(value, name))
        else:
            names.append(name)
    return names


def _source(layers, name: str) -> str | None:
    """Path of the highest layer that sets anything at `name`."""
    return next(
        (str(layer.path) for layer in reversed(layers) if _field(layer.data, name) is not _MISSING),
        None,
    )


def _identifiers(data_store: DataStore, scope: str, identifiers: list[str] | None) -> list[str]:
    if identifiers is None:
        return list_scope_identifiers(data_store, scope)
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
    """Resolve `fields` for each identifier of `scope`.

    `identifiers` limits the result to those identifiers, in the given order; an identifier
    with no folder resolves to the lower layers. `sources[name]` is the highest layer that
    sets anything at `name`. When `name` resolves to a non-empty object, `sources` also has
    an entry for every leaf below it, so each field is attributed to its own file.
    """
    items = []
    for identifier in _identifiers(data_store, scope, identifiers):
        config = get_config(
            data_store,
            namespace,
            mode=mode,
            scope_identifiers={scope: identifier},
            include_layers=True,
        )
        names = fields if fields is not None else _field_names(config.data)
        values = {}
        sources = {}
        for name in names:
            value = _field(config.data, name)
            values[name] = None if value is _MISSING else value
            sources[name] = None if value is _MISSING else _source(config.layers, name)
            if isinstance(value, dict) and value:
                for leaf in _field_names(value, name):
                    sources.setdefault(leaf, _source(config.layers, leaf))
        items.append(AcrossConfigItem(identifier=identifier, values=values, sources=sources))
    return items
