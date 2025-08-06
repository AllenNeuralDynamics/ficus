################################################################################
#
#   Delete Rigs Test   
#
################################################################################


def test_delete_rig(pg_client, api_prefix):
    # Ensure there are 2 rigs
    response = pg_client.get(f"{api_prefix}/rigs")
    assert response.status_code == 200
    rigs = response.json()["output"]
    assert len(rigs) == 2
     
    # Perform deletion
    response = pg_client.delete(f"{api_prefix}/rigs/foo_1_a")
    assert response.status_code == 200

    # Ensure there is a single rig left
    response = pg_client.get(f"{api_prefix}/rigs")
    assert response.status_code == 200
    rigs = response.json()["output"]
    assert len(rigs) == 1
    assert rigs[0]['rig_name'] == "bar_2_b"


def test_delete_non_existent_rig(pg_client, api_prefix):
    response = pg_client.delete(f"{api_prefix}/rigs/fake_test_rig")
    assert response.status_code == 404
    assert response.json()['detail'] == "Rig with name fake_test_rig not found"