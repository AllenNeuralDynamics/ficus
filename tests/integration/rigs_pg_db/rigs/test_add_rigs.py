################################################################################
#
#   Add Rigs Test
#
################################################################################


def test_add_rig(pg_client, api_prefix):
    response = pg_client.post(f"{api_prefix}/rigs/", json=[
        {
            "rig_name": "FRG_1_A", 
            "hostname": "W10TEST"
        }
    ])
    rigs = response.json()["output"]
    assert len(rigs) == 1
    assert response.status_code == 200


def test_add_multiple_rigs(pg_client, api_prefix):
    response = pg_client.post(f"{api_prefix}/rigs/", json=[
        {
            "rig_name": "frg_1_b",
            "hostname": "W10TEST2"
        },
        {
            "rig_name": "frg_1_c",
            "hostname": "W10TEST3"
        }
    ])
    rigs = response.json()["output"]
    assert len(rigs) == 2
    assert response.status_code == 200


def test_add_invalid_rig_name(pg_client, api_prefix):
    response = pg_client.post(f"{api_prefix}/rigs/", json=[
        {
            "rig_name": "frg_1_a_invalid_format", 
            "hostname": "W10TEST"
        }
    ])
    print(response.json())
    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == 'string_pattern_mismatch'


def test_add_rigs_auto_formatting(pg_client, api_prefix):
    response = pg_client.post(f"{api_prefix}/rigs/", json=[
        {
            "rig_name": "FrG_1_A", 
            "hostname": "W10TeSt"
        }
    ])
    rigs = response.json()["output"]
    assert len(rigs) == 1
    assert response.status_code == 200
    assert rigs[0]["rig_name"] == "frg_1_a" # Rig name should be lowercase
    assert rigs[0]["hostname"] == "w10test" # Hostname should be lowercase


def test_add_existing_rig(pg_client, api_prefix):
    response = pg_client.post(f"{api_prefix}/rigs/", json=[
        {
            "rig_name": "FrG_1_A", 
            "hostname": "W10TeSt"
        }
    ])
    rigs = response.json()["output"]
    assert len(rigs) == 1
    assert response.status_code == 200

    response = pg_client.post(f"{api_prefix}/rigs/", json=[
        {
            "rig_name": "frg_1_a", 
            "hostname": "w10test"
        }
    ])
    assert response.status_code == 404
    # No pgcode available because sqlite is used for testing... 
    # In production, this would throw a 409 error with pgcode 23505 since we are using PostgreSQL
    assert response.json()["detail"] == "Error writing to database (no pgcode available)"

