from copy import deepcopy
from typing import Any


def _deep_update(mapping: dict, *updating_mappings: dict) -> dict:
    """
    Merge two dictionaries together, with values from the updating_mapping taking precedence over
    mapping. Merges deeply (nested dictionaries will also merge) and handles overriding types.

    Parameters:
    -----------
        mapping: dict
            The main dictionary to merge into.
        updating_mappings: dict
            Dictionary with overrides to merge into the main dictionary.
    Returns:
    --------
        dict
            The merged dictionary.
    """
    updated_mapping = deepcopy(mapping)
    for updating_mapping in updating_mappings:
        for k, v in updating_mapping.items():
            if (
                k in updated_mapping
                and isinstance(updated_mapping[k], dict)
                and isinstance(v, dict)
            ):
                updated_mapping[k] = _deep_update(updated_mapping[k], v)
            else:
                updated_mapping[k] = v
    return updated_mapping


def _deep_update_existing_destructive(dest, source):
    """
    Recursively merge 'source' into 'dest' only if the keys exist in 'target'.
    Keys that are successfully merged are removed from 'source'.
    """
    # Snapshot of keys to avoid changing dict size during iteration.
    keys_to_process = list(source.keys())
    for key in keys_to_process:
        if key in dest:
            # Case 1: Both values are nested dictionaries -> Recurse deeper
            if isinstance(dest[key], dict) and isinstance(source[key], dict):
                _deep_update_existing_destructive(dest[key], source[key])
                # If the nested source dict is now entirely empty, remove it
                if not source[key]:
                    source.pop(key)
            # Case 2: dest is not a dict or source is a flat value -> Overwrite & pop from source
            else:
                dest[key] = source.pop(key)

def deep_diff(dict1: dict, dict2: dict) -> tuple[dict, dict, dict]:
    """Recursively compare dict2 against dict1.

    Returns:
    --------
        tuple[dict, dict, dict]
            ``(same, different, removed)``: keys whose values are equal in both, keys that are
            new or changed in dict2 (with dict2's values), and keys in dict1 that dict2 lacks
            (with dict1's values). A key set to None is not the same as a missing key.

    Examples
    --------
    >>> deep_diff({"a": 1, "b": {"c": 2, "d": 3}}, {"a": 1, "b": {"c": 5}, "e": None})
    ({'a': 1}, {'b': {'c': 5}, 'e': None}, {'b': {'d': 3}})
    """
    same: dict = {}
    different: dict = {}
    removed: dict = {}
    for key, value in dict2.items():
        if key not in dict1:
            different[key] = value
        elif isinstance(value, dict) and isinstance(dict1[key], dict):
            nested_same, nested_different, nested_removed = deep_diff(dict1[key], value)
            if nested_same:
                same[key] = nested_same
            if nested_different:
                different[key] = nested_different
            if nested_removed:
                removed[key] = nested_removed
        elif value == dict1[key]:
            same[key] = value
        else:
            different[key] = value
    for key, value in dict1.items():
        if key not in dict2:
            removed[key] = value
    return same, different, removed


def flatten_recursive_dict(mapping: dict, key_prefix: str = "") -> dict[str, Any]:
    """Flatten a nested dictionary, stringifying keys with dot notation for nested keys.

    An empty dict is kept as a value, so a field set to ``{}`` isn't lost.

    Examples
    --------
    >>> flatten_recursive_dict({'a': 1, 'b': {'c': 2, 'd': 3}, 'e': {}})
    {'a': 1, 'b.c': 2, 'b.d': 3, 'e': {}}
    """
    flat_dict = {}
    for key, value in mapping.items():
        key = f"{key_prefix}.{key}" if key_prefix else str(key)
        if isinstance(value, dict) and value:
            flat_dict.update(flatten_recursive_dict(value, key_prefix=key))
        else:
            flat_dict[key] = value
    return flat_dict
