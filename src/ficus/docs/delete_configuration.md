# Delete Config 

Delete config file.

## Example 

Zookeeper structure:

```
defaults/
  software_a/
    default.yml
    config.yml
computers/
  w10dt000001/
    default.yml
    config.yml
```

Request: 

```
DELETE /api/configs/software_a/config.yml
```

Response:

```
200 OK

{
  "message": "Successfully deleted configuration file",
  "details": {
    "path": "/defaults/software_a/config.yml"
  }
}
```