################################################################################
#
#   Delete Rigs Test   
#
################################################################################


def test_delete_rig(client):
    # Ensure there are 2 rigs
    response = client.get("/api/v1beta/rigs")
    assert response.status_code == 200
    rigs = response.json()["output"]
    assert len(rigs) == 2
     
    # Perform deletion
    response = client.delete("/api/v1beta/rigs/foo_1_a")
    assert response.status_code == 200

    # Ensure there is a single rig left
    response = client.get("/api/v1beta/rigs")
    assert response.status_code == 200
    rigs = response.json()["output"]
    assert len(rigs) == 1
    assert rigs[0]['rig_name'] == "bar_2_b"


def test_delete_non_existent_rig(client):
    response = client.delete("/api/v1beta/rigs/fake_test_rig")
    assert response.status_code == 404
    assert response.json()['detail'] == "Rig with name fake_test_rig not found"