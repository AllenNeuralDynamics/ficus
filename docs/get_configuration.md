# Get Config File

Get constructed config file from the following sources:

- ``/defaults/{namespace}/defaults.yml``
- ``/defaults/{namespace}/{filename}``
- ``/computers/{hostname}/{namespace}/defaults.yml`` (if hostname provided)
- ``/computers/{hostname}/{namespace}/{filename}`` (if hostname provided)
- ``/subjects/{subject_id}/{namespace}/defaults.yml`` (if subject_id provided)
- ``/subjects/{subject_id}/{namespace}/{filename}`` (if subject_id provided)

The list above is ordered by the precedence of merging from lowest to highest. Lower precedence fields will get overwritten by higher precedence fields. If a field doesn't exist, it will get appended. 

If a **filename** isn't provided, ficus will retrieve the default file by default. The default file can be saved as a yml, yaml or json file. There will only be 1 default file per namespace. If for some reason two default file were saved into a namespace, it will return the first default file it finds (order of default files = yml, yaml, json).

If **merge** is set to ``False``, ficus will pull the config file from:

- defaults, if no scopes given
- scope, if a single scope is given (either hostname or subject_id)
- highest precedence scope, if two scopes are given (hostname AND subject_id) - will return subject_id/<namespace>/file


## Example

Zookeeper structure:

```
defaults/
  software_a/
    default.yml
    config.yml
computers/
  w10dt000001/
    software_a/
      default.yml
      config.yml
subjects/
  614173/
    software_a/
      config.yml
```

File Content: 

```
defaults/software_a/default.yml
{
  "defaults-default-value": "the one ring" 
}

defaults/software_a/config.yml
{
  "name": "config",
  "scope": "default",
  "default-layer-value": "beep beep"
}

computers/w10dt000001/software_a/default.yml
{
  "computers-default-value": "to rule them all"
}

computers/w10dt000001/software_a/config.yml
{
  "scope": "w10dt000001"
  "computer-layer-value": "boop boop"
}

subjects/614174/software_a/config.yml
{
  "subject-layer-value": "woohoo"
}
```

Request: 

```
GET /v1/namespaces/software_a/config?filename=config.yml&hostname=w10dt000001&subject_id=614173&merge=true
```

Response:

```
200 OK

{
  "message": "Successfully retrieved configuration file",
  "details": {
    "files": [
      "/scratch/defaults/software_a/default.yml",
      "/scratch/defaults/software_a/config.yml"
      "/scratch/computers/w10dt000001/software_a/default.yml",
      "/scratch/computers/w10dt000001/software_a/config.yml"
      "/scratch/subjects/614173/software_a/config.yml",
    ]
  },
  "data": {
    "default-default-value": "the one ring",
    "computer-default-value": "to rule them all", 
    "name": "config",  
    "scope": "w10dt000001",  
    "default-layer-value": "beep beep",
    "computer-layer-value": "boop boop",
    "subject-layer-value": "woohoo",
  }
}
```




