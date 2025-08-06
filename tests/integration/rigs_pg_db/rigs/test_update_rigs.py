################################################################################
#
#   Update Rigs Test   
#
################################################################################


def test_update_rigname_and_hostname(pg_client, api_prefix):
    response = pg_client.patch(f"{api_prefix}/rigs/foo_1_a", json={
        "rig_name": "foonew_3_c", 
        "hostname": "w11test-foonew"
    })
    assert response.status_code == 200

    # Perform get request to ensure it exists
    response = pg_client.get(f"{api_prefix}/rigs/foonew_3_c")
    assert response.status_code == 200
    rigs = response.json()["output"]
    assert rigs["rig_name"] == "foonew_3_c"
    assert rigs["hostname"] == "w11test-foonew"


def test_update_rigname_only(pg_client, api_prefix):
    response = pg_client.patch(f"{api_prefix}/rigs/foo_1_a", json={
        "rig_name": "foonew_3_c", 
    })
    assert response.status_code == 200

    response = pg_client.get(f"{api_prefix}/rigs/foonew_3_c")
    assert response.status_code == 200
    rigs = response.json()["output"]
    assert rigs["rig_name"] == "foonew_3_c"
    assert rigs["hostname"] == "w11test-foo"


def test_update_hostname_only(pg_client, api_prefix):
    response = pg_client.patch(f"{api_prefix}/rigs/foo_1_a", json={
        "hostname": "w11test-foonew"
    })
    assert response.status_code == 200
    
    response = pg_client.get(f"{api_prefix}/rigs/foo_1_a")
    assert response.status_code == 200
    rigs = response.json()["output"]
    assert rigs["rig_name"] == "foo_1_a"
    assert rigs["hostname"] == "w11test-foonew"


def test_update_non_existing_rig(pg_client, api_prefix):
    response = pg_client.patch(f"{api_prefix}/rigs/badrig_3_bad", json={
        "rig_name": "foonew_3_c", 
    })
    assert response.status_code == 404
    assert response.json()["detail"] == 'Rig with name badrig_3_bad not found'


def test_update_invalid_new_rigname(pg_client, api_prefix):
    response = pg_client.patch(f"{api_prefix}/rigs/foo_1_a", json={
        "rig_name": "foonew_3_c_bad_format", 
    })
    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == 'string_pattern_mismatch'
 

def test_update_rig_already_exists(pg_client, api_prefix): 
    response = pg_client.patch(f"{api_prefix}/rigs/foo_1_a", json={
        "rig_name": "bar_2_b", 
    })
    assert response.status_code == 404
    # No pgcode available because sqlite is used for testing... 
    # In production, this would throw a 409 error with pgcode 23505 since we are using PostgreSQL
    assert response.json()["detail"] == "Error writing to database (no pgcode available)"
