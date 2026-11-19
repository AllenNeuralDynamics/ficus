"""Compare resolved config fields across the identifiers of one scope.

For each identifier (each rig under ``hostname``, say), resolve the config the way that identifier
sees it (defaults merged with its own leaf) and report, per requested field, the resolved value
and the leaf that set it.
"""

import itertools
from typing import Any

import glom

from ficus.core.exceptions import (
    ConfigDecodeError,
    UnsupportedFileTypeError,
)
from ficus.database.data_store import DataStore
from ficus.schemas.configs import ConfigErrorResponse, ConfigObject, FieldDeclaration, LeafRef
from ficus.services.configs import get_config
from ficus.services.discovery import list_scope_identifiers
from ficus.services.utils import DEFAULT_MODE
from ficus.utils.dict_merge import deep_diff


def get_all_field_declarations(config: ConfigObject, field: str) -> list[FieldDeclaration]:
    """Return all times a field has been declared in the leaf stack of a config, lowest-rank first
    
    Accepts a glom specifier for a nested field, e.g. "a.b.c"
    """
    declarations: list[FieldDeclaration] = []
    for leaf in config.leaves:
        try:
            value = glom.glom(leaf.data, field)
        except glom.PathAccessError:
            continue

        declarations.append(
            FieldDeclaration(
                field=field,
                value=value,
                source_leaf=LeafRef(**leaf.model_dump(exclude={"data"}))
            )
        )
    return declarations

def get_active_field_declaration(config: ConfigObject, field: str) -> FieldDeclaration | None:
    """If the field is declared in the config leaf stack, return the highest-rank declaration,
    which overrides all lower-rank declarations and ends up in the config.
    """
    declarations = get_all_field_declarations(config, field)
    return declarations[-1] if declarations else None


def get_configs_across_scope(
    data_store: DataStore,
    namespace: str,
    scope: str,
    mode: str,
) -> dict[str, ConfigObject | ConfigErrorResponse]:
    """For each identifier in the given scope, return the corresponding config object or an error"""
    configs: dict[str, ConfigObject | ConfigErrorResponse] = {}
    for identifier in list_scope_identifiers(data_store, scope, namespace=namespace):
        try:
            config = get_config(
                data_store,
                namespace,
                mode=mode,
                scope_identifiers={scope: identifier},
                include_leaves=True,
            )
            configs[identifier] = config
        except (ConfigDecodeError, UnsupportedFileTypeError) as error:
            configs[identifier] = ConfigErrorResponse(details=str(error))
            continue
    return configs

# def resolve_across(
#     data_store: DataStore,
#     namespace: str,
#     scope: str,
#     mode: str,
#     fields: list[str] | None,
# ) -> tuple[dict[str, ConfigObject | ConfigErrorResponse], dict[str, dict[str, LeafRef | None]]]:
    
#     if namespace not in list_namespaces(data_store):
#         raise InvalidNamespaceError(f"Namespace not found in defaults: {namespace}")
    
#     configs = get_configs_across_scope(data_store, namespace, scope, mode)

#     declarations: dict[str, dict[str, LeafRef | None]] = {}
#     for identifier, config in configs.items():
#         if isinstance(config, ConfigErrorResponse):
#             continue

#         if fields is None:
#             fields = list(flatten_recursive_dict(config.data).keys())

#         declarations[identifier] = {}
#         for field in fields:

#             active_declaration = get_active_field_declaration(config, field)
#             declarations[identifier][field] = active_declaration

#     return configs, declarations

def find_redundant_declarations(config: ConfigObject, field: str) -> tuple[list[FieldDeclaration], list[FieldDeclaration]]:
    """Find all redundant declarations of a field in the config leaf stack."""
    declarations = get_all_field_declarations(config, field)

    redundancies: list[FieldDeclaration] = []
    overrides: list[FieldDeclaration] = []
    for lower, higher in itertools.pairwise(declarations):
        if lower.value == higher.value:
            redundancies.append(higher)
        else: 
            overrides.append(higher)

    return redundancies, overrides
            
def find_declarations_in_scope(config: ConfigObject, field: str, scope: str, mode: str = DEFAULT_MODE) -> list[FieldDeclaration]:
    """Find all declarations of a field in the config leaf stack."""
    declarations = get_all_field_declarations(config, field)
    scoped_declarations: list[FieldDeclaration] = []
    for declaration in declarations:
        if declaration.source_leaf.mode == mode and declaration.source_leaf.scope == scope:
            scoped_declarations.append(declaration)

    return scoped_declarations

def compare_configs(
    config_1: ConfigObject, config_2: ConfigObject
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Compare two resolved configs: ``(same, different, removed)``, as in ``deep_diff``."""
    return deep_diff(config_1.data, config_2.data)