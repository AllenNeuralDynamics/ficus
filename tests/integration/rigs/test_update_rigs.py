################################################################################
#
#   Update Rigs Test   
#
################################################################################


def test_update_rigname_and_hostname(client):
    response = client.patch("/api/v1beta/rigs/foo_1_a", json={
        "rig_name": "foonew_3_c", 
        "hostname": "w11test-foonew"
    })
    assert response.status_code == 200

    # Perform get request to ensure it exists
    response = client.get("/api/v1beta/rigs/foonew_3_c")
    assert response.status_code == 200
    rigs = response.json()["output"]
    assert rigs["rig_name"] == "foonew_3_c"
    assert rigs["hostname"] == "w11test-foonew"


def test_update_rigname_only(client):
    response = client.patch("/api/v1beta/rigs/foo_1_a", json={
        "rig_name": "foonew_3_c", 
    })
    assert response.status_code == 200

    response = client.get("/api/v1beta/rigs/foonew_3_c")
    assert response.status_code == 200
    rigs = response.json()["output"]
    assert rigs["rig_name"] == "foonew_3_c"
    assert rigs["hostname"] == "w11test-foo"


def test_update_hostname_only(client):
    response = client.patch("/api/v1beta/rigs/foo_1_a", json={
        "hostname": "w11test-foonew"
    })
    assert response.status_code == 200
    
    response = client.get("/api/v1beta/rigs/foo_1_a")
    assert response.status_code == 200
    rigs = response.json()["output"]
    assert rigs["rig_name"] == "foo_1_a"
    assert rigs["hostname"] == "w11test-foonew"


def test_update_non_existing_rig(client):
    response = client.patch("/api/v1beta/rigs/badrig_3_bad", json={
        "rig_name": "foonew_3_c", 
    })
    assert response.status_code == 404
    assert response.json()["detail"] == 'Rig with name badrig_3_bad not found'


def test_update_invalid_new_rigname(client):
    response = client.patch("/api/v1beta/rigs/foo_1_a", json={
        "rig_name": "foonew_3_c_bad_format", 
    })
    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == 'string_pattern_mismatch'
 

def test_update_rig_already_exists(client): 
    response = client.patch("/api/v1beta/rigs/foo_1_a", json={
        "rig_name": "bar_2_b", 
    })
    assert response.status_code == 404
    # No pgcode available because sqlite is used for testing... 
    # In production, this would throw a 409 error with pgcode 23505 since we are using PostgreSQL
    assert response.json()["detail"] == "Error writing to database (no pgcode available)"
