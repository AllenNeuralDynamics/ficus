# Post Config

Add configuration file to zookeeper. 

- If filename is ``default.(yml|yaml|json)`` treat as default file.
- If hostname provided, treat as computer specific override.
- If subject_id provided, treat as subjects specific override.

## Example 

Request: 

```
POST /v1/namespaces/software_a/config/config.yml

{
    "name": "example-config",
    "data": "test beep beep"
}
```

Response:

```
200 OK

{
  "message": "Successfully added configuration file",
  "details": {
    "path": "/defaults/software_a/config.yml"
  }
  "data": {
    "name": "example-config",
    "data": "test beep beep"
  }
}
```

## Example - hostname override file

Request: 

```
POST /v1/computers/w10dt000001/namespaces/software_a/config/config.yml

{
    "name": "example-config",
    "data": "test beep beep"
}
```

Response:

```
200 OK

{
  "message": "Successfully added configuration file",
  "details": {
    "path": "/computers/w10dt000001/software_a/config.yml"
  }
  "data": {
    "name": "example-config",
    "data": "test beep beep"

  }
}
```




