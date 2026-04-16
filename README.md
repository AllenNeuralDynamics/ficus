# FICUS

[![License](https://img.shields.io/badge/license-MIT-brightgreen)](LICENSE)

Ficus: REST API to handle configuration management to SIPE's internal configuration storage (zookeeper). 

## Configuration Organization Structure

Here are some key vocabulary this API uses:

- namespace: abstract identifier to group configuration files with (ex. stagewidget, waterlog, open-ephys, etc) 
- hostnames: identifier for a specific computer (ex. w10dt100450, SAKUMA, etc)

Below is the directory structure in which config files are stored in zookeeper

```
defaults/
├── open_ephys/
│   ├── default.yml
│   ├── default.json
│   ├── config.yml
│   └── galen.yml
├── vr_frg/
│   ├── default.yml
│   └── with_sniff_detector.yml
└── waterlog/
    └── default.yml
computer/
├── w10dtburno/
│   └── vr_frg/
│       ├── default.yaml
│       └── task_specific_setting.yml
├── w10dt123123/
│   └── waterlog/
│       ├── default.json
│       └── config.yml
└── w10dtgawk/
    └── open_ephys/
        └── galen.yml
```

This organizational structure contains two layers that generate a config based on a structured override pattern. The layers contain configuration files, and based on the layer, determines the resulting config.
1. Default layer - applied to all rigs
    - Starts with ``defaults/{namespace}/default.yml`` 
    - ``defaults/{namespace}/{filename}`` merges with above via deep update.
2. Computer layer (applied to specific rigs)
    - ``computers/{hostname}/{namespace}/default.yml`` merges with previously merged configs in Defaults layer.
    - ``computers/{hostname}/{namespace}/{filename}`` merges with above with deep update. 

When looking for default files in either Default or Computer layer, it will check the following file extensions in this specific order, first one found will be the primary default file. Ideally, there should only be a single "default file" in each directory. This is enforced with the write endpoint.

    .yml -> .yaml -> .json

Below is the precedence of merging config files from lowest to highest. Lower precedence fields will get overwritten by higher precedence fields. If a field doesn't exist, it will get appended. 

    defaults/{namespace}/default.yml -> defaults/{namespace}/{filename} -> computers/{hostname}/{namespace}/default.yml -> computers/{hostname}/{namespace}/{filename} 

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
