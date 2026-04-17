# Get Config File No Merge

Get a single config file from a single sources. Does not merge config files together. 

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

Request: 

```
GET /api/configs/no-merge/software_a/w10dt000001/config.yml
```

Response:

```
200 OK

{
  "message": "Successfully retrieved configuration file",
  "details": {
    "file": "/scratch/computers/w10dt000001/software_a/config.yml"
  },
  "data": {
    "name": "config",  
    "computer-layer-value": "boop boop",
    "scope": "w10dt000001",  
  }
}
```




