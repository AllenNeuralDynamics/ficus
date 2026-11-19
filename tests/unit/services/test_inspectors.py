import pytest

from ficus.schemas.configs import ConfigObject, Leaf
from ficus.services.inspectors import (
    compare_configs,
    find_declarations_in_scope,
    find_redundant_declarations,
    get_active_field_declaration,
    get_all_field_declarations,
)
from ficus.utils.dict_merge import _deep_update


def _leaf(scope, data, identifier=None, mode="default"):
    return Leaf(
        namespace="software_a",
        scope=scope,
        scope_identifier=identifier,
        mode=mode,
        suffix=".json",
        data=data,
    )


def _config(*leaves):
    return ConfigObject(
        data=_deep_update({}, *(leaf.data for leaf in leaves)),
        namespace="software_a",
        mode="default",
        scope_identifiers={},
        override_stack=[],
        leaves=list(leaves),
    )


DEFAULTS = _leaf(None, {"camera": {"frame_rate": 30, "exposure": 10}})


def test_declarations_need_leaves():
    config = _config(DEFAULTS).model_copy(update={"leaves": None})
    with pytest.raises(ValueError, match="include_leaves"):
        get_all_field_declarations(config, "camera")


def test_all_declarations_hold_each_leafs_own_value():
    rig = _leaf("hostname", {"camera": {"frame_rate": 60}}, "rig-1")
    declarations = get_all_field_declarations(_config(DEFAULTS, rig), "camera")
    assert [d.value for d in declarations] == [
        {"frame_rate": 30, "exposure": 10},
        {"frame_rate": 60},
    ]
    assert [d.source_leaf.scope for d in declarations] == [None, "hostname"]


def test_active_declaration_is_the_highest():
    rig = _leaf("hostname", {"camera": {"frame_rate": 60}}, "rig-1")
    active = get_active_field_declaration(_config(DEFAULTS, rig), "camera.frame_rate")
    assert (active.value, active.source_leaf.scope_identifier) == (60, "rig-1")
    assert get_active_field_declaration(_config(DEFAULTS, rig), "missing") is None


def test_no_active_declaration_when_a_higher_leaf_replaces_the_parent():
    rig = _leaf("hostname", {"camera": "off"}, "rig-1")
    config = _config(DEFAULTS, rig)
    assert config.data == {"camera": "off"}
    assert get_active_field_declaration(config, "camera.frame_rate") is None
    assert get_active_field_declaration(config, "camera").value == "off"


def test_repeating_an_inherited_value_is_redundant():
    same = _leaf("hostname", {"camera": {"frame_rate": 30}}, "rig-1")
    changed = _leaf("subject_id", {"camera": {"frame_rate": 60}}, "mouse-1")
    redundant, overrides = find_redundant_declarations(_config(DEFAULTS, same, changed), "camera")
    assert [d.source_leaf.scope for d in redundant] == ["hostname"]
    assert [d.source_leaf.scope for d in overrides] == ["subject_id"]


def test_the_first_declaration_is_neither_redundant_nor_an_override():
    only_rig = _leaf("hostname", {"new_field": 1}, "rig-1")
    assert find_redundant_declarations(_config(DEFAULTS, only_rig), "new_field") == ([], [])


def test_declarations_in_scope_filter_by_scope_and_mode():
    rig = _leaf("hostname", {"camera": {"frame_rate": 60}}, "rig-1")
    rig_mode = _leaf("hostname", {"camera": {"frame_rate": 90}}, "rig-1", mode="fast")
    config = _config(DEFAULTS, rig, rig_mode)

    def values(field, scope, mode="default"):
        return [d.value for d in find_declarations_in_scope(config, field, scope, mode)]

    assert values("camera.frame_rate", "hostname") == [60]
    assert values("camera.frame_rate", "hostname", "fast") == [90]
    assert values("camera.exposure", None) == [10]


def test_compare_configs_reports_removed_keys():
    a = _config(_leaf(None, {"camera": {"frame_rate": 30, "exposure": 10}}))
    b = _config(_leaf(None, {"camera": {"frame_rate": 60}}))
    same, different, removed = compare_configs(a, b)
    assert same == {}
    assert different == {"camera": {"frame_rate": 60}}
    assert removed == {"camera": {"exposure": 10}}
