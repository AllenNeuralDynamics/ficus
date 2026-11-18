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

def deep_diff(dict1: dict, dict2: dict) -> tuple[dict, dict]:
    """Recursively compare dict2 against dict1 and return keys that are different in dict2."""
    same = {}
    diff = {}
    for key in dict2:
        if isinstance(dict2[key], dict) and isinstance(dict1.get(key), dict):
            nested_same, nested_diff = deep_diff(dict1[key], dict2[key])
            if nested_diff:
                diff[key] = nested_diff
            if nested_same:
                same[key] = nested_same
        elif dict2[key] != dict1.get(key):
            diff[key] = dict2[key]
        elif dict2[key] == dict1.get(key):
            same[key] = dict2[key]
    return same, diff


def flatten_recursive_dict(mapping: dict, key_prefix: str = "") -> dict[str, Any]:
    """Flatten a nested dictionary, stringifying keys with dot notation for nested keys.
    
    Examples
    --------
    >>> d = {'a': 1, 'b': {'c': 2, 'd': 3}}
    >>> flatten_recursive_dict(d)
    {'a': 1, 'b.c': 2, 'b.d': 3}

    """
    flat_dict = {}
    for key, value in mapping.items():
        key = f"{key_prefix}.{key}" if key_prefix else str(key)
        if isinstance(value, dict):
            flat_dict.update(flatten_recursive_dict(value, key_prefix=key))
        else:
            flat_dict[key] = value
    return flat_dict