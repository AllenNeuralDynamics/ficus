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
    updated_mapping = mapping.copy()
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
