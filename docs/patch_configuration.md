# Patch Update Config

Update an existing configuration file with new fields. 

- If field exists, override with new field values.
- If field doesn't exist, append new fields to config. 
- Overriding nested fields is supported.
- Errors when there is no existing file.

## Example 

File: 

```
/defaults/software_a/config.yml

{
    "name": "example-config"
}
```

Request: 

```
PATCH /v1/namespaces/software_a/config/config.yml
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
  "data": {
    "name": "example-config",
    "data": "test beep beep"
  }
}
```