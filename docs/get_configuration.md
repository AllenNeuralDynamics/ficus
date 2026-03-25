# Get Config File

Get constructed config file from the following sources:

- ``/defaults/{namespace}/defaults.yml``
- ``/defaults/{namespace}/{filename}``
- ``/computers/{hostname}/{namespace}/defaults.yml`` (if hostname provided)
- ``/computers/{hostname}/{namespace}/{filename}`` (if hostname provided)

Below is the precedence of merging config files from lowest to highest. Lower precedence fields will get overwritten by higher precedence fields. If a field doesn't exist, it will get appended. 

    defaults/{namespace}/default.yml -> defaults/{namespace}/{filename} -> computers/{hostname}/{namespace}/default.yml -> computers/{hostname}/{namespace}/{filename} 

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
```

File Content: 

```
defaults default.yml
{
  "defaults-default-value": "the one ring" 
}

defaults config.yml
{
  "name": "config",
  "scope": "default",
  "default-layer-value": "beep beep"
}

computers default.yml
{
  "computers-default-value": "to rule them all"
}

computers config.yml
{
  "scope": "w10dt000001"
  "computer-layer-value": "boop boop"
}
```

Request: 

```
GET /api/configs/software_a/w10dt000001
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
    ]
  },
  "data": {
    "default-default-value": "the one ring",
    "computer-default-value": "to rule them all", 
    "name": "config",  
    "default-layer-value": "beep beep",
    "computer-layer-value": "boop boop",
    "scope": "w10dt000001",  
  }
}
```




