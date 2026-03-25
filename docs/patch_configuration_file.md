# Patch Update Config (Upload File)

Update an existing configuration file with new fields. 

- If field exists, override with new field values.
- If field doesn't exist, append new fields to config. 
- Overriding nested fields is supported.
- Errors when there is no existing file.

## Example 

File: 

```
config.yml

{
    "name": "example-config"
    "data": "hello"
}
```

Request: 

```
PATCH /api/configs/software_a/config.yml

multipart/form-data (file)
{
    "name": "example-config",
    "data": "test beep beep"
}
```

Response:

```
200 OK

{
  "message": "Successfully updated configuration file",
  "details": {
    "path": "/defaults/software_a/config.yml"
  }
}
```