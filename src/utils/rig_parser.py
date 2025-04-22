import re


def parse_rig_name(rig: str) -> tuple[str, str | None, str | None]:
    """Parse rig/comp names in this format: `RIG.1-CompType` or `RIG.1`.

    Returns:
        rig_type: The type of rig (e.g., `RIG`).
        instance: The instance number (e.g., `1`). If not present, returns None
        comp_type: The component type (e.g., `CompType`). If not present, returns None.

    Examples:
        >>> parse_rig_name("RIG.1-CompType") == ("RIG", "1", "CompType")
        True
        >>> parse_rig_name("WL.7") == ("WL", "7", None)
        True
    """
    rig_regex = r"^(?P<rig_type>[A-Z]+)(?:\.(?P<instance>[0-9]+)(?:-(?P<comp_type>[A-Za-z]+))?)?$"

    if match := re.match(rig_regex, rig):
        rig_type = match.group("rig_type")
        instance = match.group("instance")
        comp_type = match.group("comp_type")
        return rig_type, instance, comp_type
    else:
        return rig, None, None


if __name__ == "__main__":
    import doctest

    doctest.testmod()
