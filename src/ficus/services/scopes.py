import re

from ficus.database.data_store import DataStore

# Scope names share URLs with Ficus's own query parameters in the legacy ?<scope>=<id> style,
# so these can never be scopes. `defaults` is the folder beside every scope.
RESERVED_SCOPE_NAMES = frozenset(
    {
        "defaults",
        "mode",
        "scope",
        "scope_identifier",
        "suffix",
        "overwrite",
        "overwrite_defaults",
        "append_new_fields_to_last_scope",
        "create_missing_namespace",
        "dry_run",
        "layers",
        "fields",
        "identifiers",
        "namespace",
        "lowest_scope_only",
        "path",
        "data",
    }
)
SCOPE_NAME = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")


class InvalidScopeNameError(ValueError):
    pass


class ScopeExistsError(ValueError):
    pass


def validate_scope_name(name: str) -> None:
    if not SCOPE_NAME.fullmatch(name):
        raise InvalidScopeNameError(
            f"Invalid scope name {name!r}: use lowercase letters, digits, '_' or '-', "
            "starting with a letter."
        )
    if name in RESERVED_SCOPE_NAMES:
        raise InvalidScopeNameError(f"{name!r} is reserved and can't be a scope.")


def add_scope(data_store: DataStore, name: str) -> list[str]:
    """Create a scope: its folder, and the last place in the precedence (it wins over the others).

    This is the only way to create a scope; saving a config never does.
    """
    validate_scope_name(name)
    order = data_store.reload_scopes()
    if name in order:
        raise ScopeExistsError(f"Scope {name!r} already exists.")
    scope_path = data_store.rootdir / name
    if not data_store.exists(scope_path):
        data_store.create(scope_path, data=None)
    new_order = order + [name]
    data_store.write_scope_order(new_order)
    return new_order
