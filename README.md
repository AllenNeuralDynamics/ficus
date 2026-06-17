# FICUS

[![License](https://img.shields.io/badge/license-MIT-brightgreen)](LICENSE)

Ficus: data store management, merge strategy, and REST API to handle software configs in a selectable data store


## Problem Overview

* don't repeat yourself
  * manage subtle differences between configs easily while maintaining commonalities in one place. 
* maintain configs in one place to make them easier to edit in bulk if their underlying structure (schema) changes.

## Configuration Organization Structure

Here are some key vocabulary this API uses:

- scope: a config override level represented as a top-level folder.
- *scope identifier*: identifier within a scope represented as a folder within a *scope*.
- namespace: abstract identifier to group configuration files across scopes (ex. stagewidget, waterlog, open-ephys, etc) 
- hostname: identifier for a specific computer (ex. w10dt100450, SAKUMA, etc)
- subject_id: identifier for a specific subject (ex. 614173, etc)
- *scope resolution order*: the scope order in which configs are merged.

```
scope_name/
├── scope_identifier/
│   └── namespace/
│       └── default.yml
```

Below is the directory structure in which config files are stored in zookeeper.

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
hostname/
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
subject_id/
├── 614173/
│   └── vr_frg/
│       ├── default.yaml
│       └── config.yml
```

> [!NOTE]
> The *defaults* scope has an implied default scope identifier which is omitted.

This organizational structure contains a set of layers called scopes.
The (predetermined) *scope resolution order* generates a config based on a structured override pattern.
The layers contain configuration files, and based on the layer, determines the resulting config.
1. Default layer - applied to all rigs
    - Starts with ``defaults/{namespace}/default.yml`` 
    - ``defaults/{namespace}/{filename}`` merges with above via deep update.
2. Computers layer (applied to specific rigs)
    - ``computers/{hostname}/{namespace}/default.yml`` merges with previously merged configs in Defaults layer.
    - ``computers/{hostname}/{namespace}/{filename}`` merges with above with deep update. 
2. Scopes layer (applied to specific rigs)
    - ``subjects/{subject_id}/{namespace}/default.yml`` merges with previously merged configs in Defaults layer.
    - ``subjects/{subject_id}/{namespace}/{filename}`` merges with above with deep update. 

When looking for default files in either *defaults* or *computer_id* layer, it will check the following file extensions in this specific order, first one found will be the primary default file.
Ideally, there should only be a single "default file" in each directory. This is enforced with the write endpoint.

    .yml -> .yaml -> .json

Below is the precedence of merging config files from lowest to highest. Lower precedence fields will get overwritten by higher precedence fields. If a field doesn't exist, it will get appended. 

- defaults/{namespace}/default.yml 
- defaults/{namespace}/{filename} 
- computers/{hostname}/{namespace}/default.yml 
- computers/{hostname}/{namespace}/{filename} 
- subjects/{subject_id}/{namespace}/default.yml 
- subjects/{subject_id}/{namespace}/{filename} 

## Examples

### Subject-Specific Overrides
The user, specimen, sample, etc. has persistent values that require changes to the software config.

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
