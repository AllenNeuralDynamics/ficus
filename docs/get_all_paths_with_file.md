# Get Paths with Config File

Get all paths containing a specific **namespace** and **config file**. 

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
  w11dt999999/
    software_a/
      config.yml
  DT714923/
    stagewidget/
      config.yml
```

Request: 

```
GET /api/configs/list_paths/software_a/config.yml
```

Response:

```
200 OK

{
  "message": "Successfully retrieved configuration file",
  "details": {},
  "data": [
    "/defaults/software_a/config.yml",
    "/computers/w10dt000001/software_a/config.yml",
    "/computers/w11dt999999/software_a/config.yml"
  ]
}
```




