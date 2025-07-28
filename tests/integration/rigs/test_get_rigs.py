################################################################################
#
#   Get Rigs Test
#
################################################################################


def test_get_rigs(client):
    response = client.post("/api/v1beta/rigs/", json=[
        {
            "rig_name": "FRG_1_A", 
            "hostname": "W10TEST"
        }
    ])
    rigs = response.json()["output"]
    assert len(rigs) == 1
    assert response.status_code == 200

    response = client.get("/api/v1beta/rigs/")
    assert response.status_code == 200
    assert len(response.json()["output"]) == 1
    assert response.json()["output"][0]["rig_name"] == "frg_1_a"  
 

def test_get_rigs_empty(client):
    response = client.get("/api/v1beta/rigs/")
    assert response.status_code == 200
    assert response.json()["output"] == []


def test_get_rigs_with_filters(client): 
    response = client.post("/api/v1beta/rigs/", json=[
        {
            "rig_name": "frg_1_b",
            "hostname": "W10TEST2"
        },
        {
            "rig_name": "wot_2_c",
            "hostname": "W10beepboop3"
        }
    ])
    rigs = response.json()["output"]
    assert len(rigs) == 2
    assert response.status_code == 200

    # rig_type filter
    response = client.get("/api/v1beta/rigs/?rig_type=frg")
    assert response.status_code == 200
    assert len(response.json()["output"]) == 1
    assert response.json()["output"][0]["rig_name"] == "frg_1_b"

    # instance filter
    response = client.get("/api/v1beta/rigs/?instance=1")
    assert response.status_code == 200
    assert len(response.json()["output"]) == 1
    assert response.json()["output"][0]["rig_name"] == "frg_1_b"

    # comp_type filter
    response = client.get("/api/v1beta/rigs/?comp_type=b")
    assert response.status_code == 200
    assert len(response.json()["output"]) == 1
    assert response.json()["output"][0]["rig_name"] == "frg_1_b"

    # hostname filter
    response = client.get("/api/v1beta/rigs/?hostname=w10test2")
    assert response.status_code == 200
    assert len(response.json()["output"]) == 1
    assert response.json()["output"][0]["rig_name"] == "frg_1_b"

    # multiple filters
    response = client.get("/api/v1beta/rigs/?rig_type=wot&instance=2")
    assert response.status_code == 200
    assert len(response.json()["output"]) == 1
    assert response.json()["output"][0]["rig_name"] == "wot_2_c"


################################################################################
#
#   Get Rig Test
#
################################################################################


def test_get_rig(client):
    response = client.post("/api/v1beta/rigs/", json=[
        {
            "rig_name": "FRG_1_A", 
            "hostname": "W10TEST"
        }
    ])
    rigs = response.json()["output"]
    assert len(rigs) == 1
    assert response.status_code == 200

    response = client.get("/api/v1beta/rigs/frg_1_a/")
    assert response.status_code == 200
    assert response.json()["output"]["rig_name"] == "frg_1_a"
 

def test_get_rig_invalid(client):
    response = client.get("/api/v1beta/rigs/frg_1_a/")
    assert response.status_code == 404
    assert response.json()["detail"] == "Rig with name frg_1_a not found"

