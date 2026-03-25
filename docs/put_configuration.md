# Put Replace Config

Overwrite an existing configuration file with a new file. 

- Only overwrites the content of the new file (does not change existing filename).
- If hostname provided, search for existing config in ``/computers/{hostname}``.
- Creates file if it doesn't exist.

## Example 

Request: 

```
POST /api/configs/software_a/config.yml

{
    "name": "example-config",
    "data": "test beep beep"
}
```

Response:

```
200 OK

{
  "message": "Successfully replaced configuration file",
  "details": {
    "path": "/defaults/software_a/config.yml"
  }
}
```

## Example - hostname override file

Request: 

```
POST /api/configs/w10dt000001/software_a/config.yml

{
    "name": "example-config",
    "data": "test beep beep"
}
```

Response:

```
200 OK

{
  "message": "Successfully replaced configuration file",
  "details": {
    "path": "/computers/w10dt000001/software_a/config.yml"
  }
}
```




