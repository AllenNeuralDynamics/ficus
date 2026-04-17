# Get Files in All Paths 

Given a namespace, look in all paths (defaults, hostname overrides) and grab all the files within those paths.

If hostname is given, search in defaults and only in that hostname.

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
GET /api/configs/list_files/software_a
```

Response:

```
200 OK

{
  "message": "Successfully retrieved configuration file",
  "details": {},
  "data": [
    "/defaults/software_a/config.yml",
    "/defaults/software_a/default.yml",
    "/computers/w10dt000001/software_a/config.yml",
    "/computers/w10dt000001/software_a/default.yml",
    "/computers/w11dt999999/software_a/config.yml"
  ]
}
```
## Example - Hostname 

Zookeeper structure: same as previous example

Request: 

```
GET /api/configs/list_files/software_a/w10dt000001
```

Response:

```
200 OK

{
  "message": "Successfully retrieved configuration file",
  "details": {},
  "data": [
    "/defaults/software_a/config.yml",
    "/defaults/software_a/default.yml",
    "/computers/w10dt000001/software_a/config.yml",
    "/computers/w10dt000001/software_a/default.yml",
  ]
}
```





