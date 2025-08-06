################################################################################
#
#   Get Rigs Test
#
################################################################################


def test_get_rigs(client, api_prefix):
    response = client.get(f"{api_prefix}/rigs/")
    assert response.status_code == 200
    rigs = response.json()["output"]
    assert len(rigs) == 2
    assert rigs[0]["rig_name"] == "foo_1_a"  
    assert rigs[1]["rig_name"] == "bar_2_b"  
 

def test_get_rigs_empty(client, api_prefix):
    # Delete default values
    response = client.delete(f"{api_prefix}/rigs/foo_1_a")
    assert response.status_code == 200
    response = client.delete(f"{api_prefix}/rigs/bar_2_b")
    assert response.status_code == 200
    
    # Test getting rigs with empty table
    response = client.get(f"{api_prefix}/rigs/")
    assert response.status_code == 200
    assert response.json()["output"] == []


def test_get_rigs_with_filters(client, api_prefix): 
    # rig_type filter
    response = client.get(f"{api_prefix}/rigs/?rig_type=foo")
    assert response.status_code == 200
    assert len(response.json()["output"]) == 1
    assert response.json()["output"][0]["rig_name"] == "foo_1_a"

    # instance filter
    response = client.get(f"{api_prefix}/rigs/?instance=1")
    assert response.status_code == 200
    assert len(response.json()["output"]) == 1
    assert response.json()["output"][0]["rig_name"] == "foo_1_a"

    # comp_type filter
    response = client.get(f"{api_prefix}/rigs/?comp_type=b")
    assert response.status_code == 200
    assert len(response.json()["output"]) == 1
    assert response.json()["output"][0]["rig_name"] == "bar_2_b"

    # hostname filter
    response = client.get(f"{api_prefix}/rigs/?hostname=w11test-foo")
    assert response.status_code == 200
    assert len(response.json()["output"]) == 1
    assert response.json()["output"][0]["rig_name"] == "foo_1_a"

    # multiple filters
    response = client.get(f"{api_prefix}/rigs/?rig_type=bar&instance=2")
    assert response.status_code == 200
    assert len(response.json()["output"]) == 1
    assert response.json()["output"][0]["rig_name"] == "bar_2_b"


################################################################################
#
#   Get Rig Test
#
################################################################################


def test_get_rig(client, api_prefix):
    response = client.get(f"{api_prefix}/rigs/foo_1_a/")
    assert response.status_code == 200
    assert response.json()["output"]["rig_name"] == "foo_1_a"
 

def test_get_rig_invalid(client, api_prefix):
    response = client.get(f"{api_prefix}/rigs/frg_1_a/")
    assert response.status_code == 404
    assert response.json()["detail"] == "Rig with name frg_1_a not found"

