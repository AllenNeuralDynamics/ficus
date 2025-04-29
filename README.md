# Calibration API

[![License](https://img.shields.io/badge/license-MIT-brightgreen)](LICENSE)

Calibration API: an API to store calibration data for various rigs at the Allen Institute.

## Design 

### Endpoints

| Endpoint                              | HTTP Method | Description                | Query Param                              |
| ------------------------------------- | ----------- | -------------------------- | ---------------------------------------- |
| /api/v1/rigs/                         | GET         | Get all rigs               | rig_type, comp_type, instance, host_name |
| /api/v1/rigs/                         | POST        | Add new rig                |                                          |
| /api/v1/rigs/{rig_name}/              | GET         | Get rig based on full name | *rig_name                                |
| /api/v1/rigs/{rig_name}/calibrations/ | GET         | Get calibrations for rig   | *rig_name, device_name                   |
| /api/v1/rigs/{rig_name}/calibrations/ | POST        | Add calibrations for rig   | *rig_name                                |
| /api/v1/calibrations/                 | GET         | Get calibrations           | device_name, rig_name, datetime          |
| /                                     | GET         | Health Check               |                                          |


### Calibration Database Schema

![](assets/database.svg)

##  Developers Guide

### Local Installation

1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/)

2. Clone project

    ```bash
    git clone https://github.com/AllenNeuralDynamics/calibration-api.git
    ```

3. Run the following code in the project to start up local instance of API server

    ```bash
    uv run fastapi dev 
    ```

4. Go to http://127.0.0.1:8000/docs to test endpoints 

### Test, Type, Lint

Use tox to run testing, typing, and linting

```bash
tox -e test,type,lint
```

### Database Connection

The PostgresSQL database is hosted on eng-tools:5432. Reach out to [Jessy](jessy.liao@alleninstitute.org) or someone from the SIPE team for credentials. 

The sql script to setup the database can be found [here](database/setup.pgsql).



