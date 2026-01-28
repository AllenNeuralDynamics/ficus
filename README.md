# FICUS

[![License](https://img.shields.io/badge/license-MIT-brightgreen)](LICENSE)

Ficus: API to handle configuration management to SIPE's internal configuration storage. 

**Current status:** read/write from zookeeper. Other datasources maybe added later.

## Zookeeper Structure

Before going into the zookeeper structure, lets go over some key vocabulary this API uses: 

- namespace: abstract identifier to group configuration files with (ex. stagewidget, waterlog, etc) 
- groups: identifier for a group of computers, for now this corresponds to comp-type from SIPE rig's nomenclature (FRG, BEH, etc)
- rigs: identifier for a specific computer (hostnames)
- scopes: the scope in which the configuration gets applied to
  - default = applies to all rigs
  - group = applies to a group of computers
  - rig = applies to a single computer

Below is the directory structure in which config files are stored in zookeeper

```
defaults/
├── stagewidget/
│   ├── config.yml
│   └── device.yml
└── waterlog/
    └── config.yml
groups/
├── FRG/
│   ├── waterlog/
│   │   └── config.yml
│   └── stagewidget/
│       └── device.yml
└── BEH/
    └── waterlog/
        └── config.yml
rigs/
└── SAKUMA/
    └── stagewidget/
        ├── config.yml
        └── device.yml
```

There are three main directories (scopes) that configs get organized to: 

- defaults: these are default configurations applied to **all computers**
- groups: these are configurations that are applied to a specific **group of computers**
- rigs: these are configurations that are applied to a specific **computer**

Below are examples of how the defaults/groups/rigs (scopes) are used to retrieve configuration files: 

- Given namespace and file name, it will return config file in defaults scope with that namespace. Example:
  - namespace = stagewidget, file_name = config.yml
  - This will get ``defaults/stagewidget/config.yml``
- Given namespace, file name, group name, it will return config file in defaults scope, but also override/append values in groups if possible. Example:
  - namespace = stagewidget, file_name = device.yml, group = FRG
  - Gets ``defaults/stagewidget/device.yml``
  - Override values in defaults with anything in ``groups/FRG/stagewidget/device.yml``
- Given namespace, file name, group name, & rig name, same behavior as group but now rigs has highest precedence when overriding. Example:
  - namespace = stagewidget, file_name = device.yml, group = FRG, rig=SAKUMA
  - Gets ``defaults/stagewidget/device.yml``
  - Override values in defaults with anything in ``groups/FRG/stagewidget/device.yml``
  - Override values in defaults + groups with anything in ``rigs/SAKUMA/stagewidget/device.yml``

With this paradigm, the configs in rigs or groups can be partial configs containing overrides only. They can also be used as different copies of configuration as well. There will be an endpoint that performs merging and endpoint to grab a specific file with no merging at all. 

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
