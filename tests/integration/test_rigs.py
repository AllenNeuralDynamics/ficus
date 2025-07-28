def test_get_rigs(client):
    response = client.get("/api/v1beta/rigs/")
    print(response.json())
    assert response.status_code == 200

def test_add_rigs(client):
    # Add single rig
    response = client.post("/api/v1beta/rigs/", json=[
        {
            "rig_name": "frg_1_a", 
            "hostname": "W10TEST"
        }
    ])
    rigs = response.json()["output"]
    assert len(rigs) == 1
    assert response.status_code == 200

    # Add multiple rigs
    response = client.post("/api/v1beta/rigs/", json=[
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

    # Add invalid rig

