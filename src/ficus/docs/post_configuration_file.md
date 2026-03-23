# Post Config (Upload File)

Given file upload, add configuration file to zookeeper. 

- If filename is ``default.(yml|yaml|json)`` treat as default file.
- If hostname provided, treat as computer specific override.

## Example 

Request: 

```
POST /api/configs/software_a/

multipart/form-data (file)
```

Response:

```
200 OK

{
  "message": "Successfully added configuration file",
  "details": {
    "path": "/defaults/software_a/config.yml"
  }
}
```

## Example - hostname override file

Request: 

```
POST /api/configs/software_a/w10dt000001

multipart/form-data (file)
```

Response:

```
200 OK

{
  "message": "Successfully added configuration file",
  "details": {
    "path": "/computers/w10dt000001/software_a/config.yml"
  }
}
```




