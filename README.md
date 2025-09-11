# FICUS

[![License](https://img.shields.io/badge/license-MIT-brightgreen)](LICENSE)

Ficus: API to handle configuration management to SIPE's internal configuration storage. 

Current status: only reads from our zookeeper server. Future work will include writing configuration into storage and potentially changing where and how the configuration is stored. 

##  Developers Guide

### Local Installation

1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/)

1. Clone project

    ```bash
    git clone https://github.com/AllenNeuralDynamics/ficus.git
    ```

1. Run the following code in the project to start up local instance of API server

    ```bash
    uv run fastapi dev 
    ```

1. Go to http://127.0.0.1:8000/docs to test endpoints 

### Test, Type, Lint

Use tox to run testing, typing, and linting

```bash
tox -e test,type,lint
```
