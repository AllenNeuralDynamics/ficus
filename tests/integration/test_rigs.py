def test_get_rigs(client):
    response = client.get("/api/v1beta/rigs/")
    print(response.json())
    assert response.status_code == 200

def test_add_rigs(client):
    # Add single rig
    response = client.post("/api/v1beta/rigs/", json=[{"rig_name": "frg_1_a", "hostname": "W10TEST"}])
    print(response.json())
    assert response.status_code == 200

    # Add multiple rigs
    response = client.get("/api/v1beta/rigs/")
    print(response.json())
    assert response.status_code == 200

    # Add invalid rig
