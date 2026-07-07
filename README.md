# FICUS

[![License](https://img.shields.io/badge/license-MIT-brightgreen)](LICENSE)

Ficus is a collection of convenience functions to manage configs in prototyping and production environments.
It features:
* Utility functions to merge configs based on a user-specifiable override hierarchy.
  * deep merge, deep save, deep delete capabilities with the option of overriding/not-overriding defaults.
  * highly flexible override setup enabling computer-specific or input-specific config overrides.
* Store, update, and maintain multiple configs for many kinds of software in one place.
* Configureable data store
  * Pull down configs from a centralized location with a REST API and client (confierge) to handle concurrent connections
  * OR run Ficus locally on a local folder to get all the benefits of hierarchical configs without needing to stand up a server.

Use cases might include:
* Maintain large configs for the same software across many rigs running that software with subtle difference between each rig.
* Manage an experimental setup on one rig with many different hardware configurations that would affect what get's launched on startup.

## Conventions
First things first, what should we be storing in a config file?

Loosely, we think of configs as managing the _starting state of the software, without any input_.
The config contains information related to the persistent structure of the software, ie: which drivers, what com ports, URLs, endpoints, hardware settings, etc.
Software "wiring" is another way to think of this.

For running programs with verbose input that changes each time you run the software, we suggest adopting the convention of a separate _job_, _experiment_, or _session_ file.
Doing so creates a clean _separation-of-concerns_ whereby configs manage structure-related information, and "job" files manage session or input-related information.

## Configuration Organization Structure

Here's some key vocabulary this API uses:

- *scope*: a config override level. Ex: `hostname`.
- *scope identifier*: identifier within a scope represented as a folder within a *scope*. Ex: `hostname=W10DTBURNO`.
- *namespace*: abstract identifier to group config files across scopes. One convention is to make a namespace for the target software that will use the config. (Ex: vr-foraging, stagewidget, waterlog, open-ephys, etc).
- *scope resolution order*: the scope order in which configs are merged.


Here's how scopes and scope identifiers resolve as a folder structure:

```
scope_name/
├── scope_identifier/
│   └── namespace/
│       └── default.yml
```

Below is an example directory structure in which configs are stored using the following scopes and namespaces:

**Scopes**
- hostname: identifier for a specific computer (ex. w10dt100450, SAKUMA, etc)
- subject_id: identifier for a specific subject (ex. 614173, etc)

**Namespaces**
- `open_ephys`: the open ephys software for running electrophysiology experiments.
- `vr_frg`: the vr-foraging software for running animal behavior experiments.

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
        └── default.yml
        └── galen.yml
subject_id/
├── 614173/
│   └── vr_frg/
│       └── default.yaml

```

> [!NOTE]
> The *defaults* scope has an implied default scope identifier which is omitted.

You can create any scopes you need (beyond `defaults`) to better adjust to your existing use case, but do note that we have been able to use the scopes `defaults`, `hostname`, and `subject_id` to accomplish all of our use cases across multiple software packages to date.

## Fetching and Merging a Config
The *scope resolution order* generates a config based on a structured override pattern.
Overrides are applied via a recursive (aka: _deep_) update function.
The result is that, for the same softare running on many computers, configs at the computer level are lean and contain only computer-specific overrides.

#### Example 1: Default Config
Here's an example request.
```python
get_config(data_store=data_store,
           namespace="open_ephys")
```
The above request pulls down the default config for the `open_ephys` software.
To construct this config, the following merges are applied.
* Within `defaults/open_ephys`, we start with `default.yml` and thats it!

#### Example 1: Default Config (Scenario 2)
Suppose the `open_ephys` software uses USB devices that have different COM Ports per computer, so we store them in a hostname-specific override.

Here's the example request.
```python
get_config(data_store=data_store,
           namespace="open_ephys",
           scope_identifiers={"hostname": "w10dtgawk"})
```
The above request pulls down the default config for the `open_ephys` software for the hostname: `w10dtgawk`.
To construct this config, the following merges are applied.
* Within `hostname/w10dtgawk/open_ephys`, we start with `default.yml` as our current config.
* Within `defaults/open_ephys`, we fetch `default.yml`. Our current config overrides (aka: `deep_update`s against) this `default.yml`.

#### Example 2: User-specific overrides for a specific machine
Suppose scientist Galen wants to use the `open_ephys` software with custom presets on one of the lab computers, so he stores them in a galen-specific config.

Here's an example request.
```python
get_config(data_store=data_store,
           namespace="open_ephys",
           scope_identifiers={"hostname": "w10dtgawk"},
           mode="galen")
```
The above request pulls down a config for the `open_ephys` software on a computer with hostname: `w10dtgawk`. The config has a specific name called `galen.yml`.
To construct this config, the following merges are applied.
* Within `hostname/w10dtgawk/open_ephys`, we start with `galen.yml` as our current config.
* Within `hostname/w10dtgawk/open_ephys`, we fetch `default.yml`. Our current config overrides this `default.yml`.
* Within `defaults/open_ephys`, we fetch `galen.yml`. Our current config overrides this `galen.yml`.
* Within `defaults/open_ephys`, we fetch `default.yml`. Our current config overrides this `default.yml`.

#### Example 3: Input-specific overrides for a specific machine
Suppose the inputs to the software have settings that alter the software config, and these settings persist each time we run the same input.
For example, with the software `vr_foraging`, each mouse has different skull shape that affects the XYZ position of the lickspout stage.
This offset can be recorded once, and it persists throughout the lifetime of that mouse, but it is part of the starting state of the `vr_foraging` software, so its values are passed in via config.

Here's an example request.
```python
get_config(data_store=data_store,
           namespace="vr_frg",
           scope_identifiers={"hostname": "w10dtburno", "subject_id": "614173"})
```
The above request pulls down a config (named default) for the `vr_frg` software on a computer with hostname: `w10dtburno` for mouse subject: 614173.
To construct this config, the following merges are applied.
* Within `subject_id/615173/vr_frg`, we start with `default.yml` as our current config.
* Within `hostname/w10dtburno/vr_fg`, we fetch `default.yml`. Our current config overrides this `default.yml`.
* Within `defaults/vr_frg`, we fetch `default.yml`. Our current config overrides this `default.yml`.

> [!NOTE]
> The `scope_identifiers` dict is ordered and specifies the merge order.

#### Example 4: Different Concurrent Hardware Configurations
Suppose the experimental software `prototome` running on pc W11XLTEST needs to be run in different states with different combinations of the hardware attached to the same computer.
Here's how we would store these configs:

```
├── defaults/
│   └── prototome/
│       └── default.yml  # settings for everything running prototome software
└── hostname/
    ├── W11XLTEST/
    │   └── prototome/
    │       ├── default.yml  # settings applying to all protome software running on this PC
    │       ├── microtome.yml  # settings for all connected hardware for the custom microtome
    │       ├── left_lasso.yml # settings for all connected hardware for the left lasso
    │       └── right_lasso.yml # settings for all connected hardware for the right lasso
    └── W11LEICA/
        └── prototome/
            └── default.yml
```

Now here's an added nuance.
Suppose these different modes can all run concurrently!

There's no built-in api function to do this, but you can manually pull down multiple configs and merge them locally.
Provided that each config can run standalone, and each config communicates with separate hardware, or can safely override shared fields, theres nothing preventing you from pulling down 3 configs and merging them.


### Scope Details for this Setup

1. `defaults` layer - applied to all rigs
    - Starts with ``defaults/{namespace}/default.yml`` 
    - ``defaults/{namespace}/{filename}`` merges with above via deep update.
2. `hostname` layer (applied to specific rigs)
    - ``computers/{hostname}/{namespace}/default.yml`` merges with previously merged configs in Defaults layer.
    - ``computers/{hostname}/{namespace}/{filename}`` merges with above with deep update. 
2. `subject_id` layer (applied to specific rigs)
    - ``subjects/{subject_id}/{namespace}/default.yml`` merges with previously merged configs in Defaults layer.
    - ``subjects/{subject_id}/{namespace}/{filename}`` merges with above with deep update. 

Below is the precedence of merging config files from lowest to highest. Lower precedence fields will get overwritten by higher precedence fields. If a field doesn't exist, it will get appended. 

- defaults/{namespace}/default.yml 
- defaults/{namespace}/{filename} 
- computers/{hostname}/{namespace}/default.yml 
- computers/{hostname}/{namespace}/{filename} 
- subjects/{subject_id}/{namespace}/default.yml 
- subjects/{subject_id}/{namespace}/{filename} 


## How to use this Structure
Use *scopes* to store properties intrinsic to the scope.
For example, the subject scope contains config values with properties intrinsic to that.

Use *namespaces* to group scopes.
We usually use software as our namespace.


## FAQs

### What file formats are supported?
Currently, we support json and yaml. Filenames within a folder must be unique, and this is enforced upon read/write.
In other words, if the config originated from a yaml, you can save it back a json, and it will convert it from yaml to json.

### Why not just have a centralized config schema across all devices that use this package?
It's worth considering: why do you need all this? If you have a common config schema across all software that uses configs, then you don't need the concept of a namespace.

In practice, this isn't always possible.
You might inherit legacy code, or it may not be practical to apply and maintain an adapter that converts a config from a shared schema to a software-specific one.

The other challenge is that this schema is intended to be a one-size-fits-all to apply to as many software packages as possible.
To date, this has been the case even in some quite strange use cases, so you if you have questions about how to adapt this project to your needs, drop us an issue!

### Do you validate configs?
Currently no. Validation is left up to the user.

### Does this system manage partial configs?
Not necessarily.
The idea with the conventions above is that, when pulling down a config and applying the merges needed to construct it, it is ready to run on the specified software.
There's nothing against using this setup to manage partial configs, but it may not lend itself as easily to doing so.


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
