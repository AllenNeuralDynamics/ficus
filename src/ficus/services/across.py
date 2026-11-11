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


def resolve_across(
    data_store: DataStore,
    namespace: str,
    scope: str,
    mode: str,
    fields: list[str] | None,
) -> list[AcrossConfigItem]:
    items = []
    for identifier in list_scope_identifiers(data_store, scope):
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
            sources[name] = next(
                (
                    str(layer.path)
                    for layer in reversed(config.layers)
                    if _field(layer.data, name) is not _MISSING
                ),
                None,
            ) if value is not _MISSING else None
        items.append(AcrossConfigItem(identifier=identifier, values=values, sources=sources))
    return items
