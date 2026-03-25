# Put Replace Config (Upload File)

Overwrite an existing configuration file with a new file. 

- Only overwrites content of the new file (does not change existing filename).
- If hostname provided, search for existing config in ``/computers/{hostname}``.
- Errors when there is no existing file.

## Example 

Request: 

```
PUT /api/configs/software_a/config.yml

multipart/form-data (file)
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

multipart/form-data (file)
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




