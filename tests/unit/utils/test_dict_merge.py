from ficus.utils.dict_merge import deep_diff, flatten_recursive_dict


def test_deep_diff_splits_same_different_and_removed():
    same, different, removed = deep_diff(
        {"a": 1, "b": {"c": 2, "d": 3}, "only_in_1": 5},
        {"a": 1, "b": {"c": 9}, "only_in_2": 6},
    )
    assert same == {"a": 1}
    assert different == {"b": {"c": 9}, "only_in_2": 6}
    assert removed == {"b": {"d": 3}, "only_in_1": 5}


def test_deep_diff_tells_a_null_from_a_missing_key():
    same, different, removed = deep_diff({"a": 1}, {"a": 1, "new": None})
    assert different == {"new": None}
    assert removed == {}
    same, different, removed = deep_diff({"a": 1, "gone": None}, {"a": 1})
    assert removed == {"gone": None}


def test_deep_diff_replaces_a_dict_with_a_value():
    _, different, removed = deep_diff({"a": {"b": 1}}, {"a": 2})
    assert different == {"a": 2}
    assert removed == {}


def test_flatten_keeps_empty_dicts():
    assert flatten_recursive_dict({"a": 1, "b": {"c": 2, "d": {}}, "e": {}}) == {
        "a": 1,
        "b.c": 2,
        "b.d": {},
        "e": {},
    }
