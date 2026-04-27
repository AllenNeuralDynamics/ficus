# Get Files in All Paths 

Given a namespace, get all files under a namespace in the defaults scope. 

If a hostname is provided, search in the computers/<hostname> scope for all files with the given namespace.

If a subject_id is provided, search in the subjects/<subject_id> scope for all files with the given namespace.

If a filename is provided, filter through the files and make sure the names match the provided filename. Handles partial matching and is case-insensitive.  

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
subjects/
  614173/
    software_a/
      config.yml
      test.yml

```

Request: 

```
GET /v1/list_files/software_a/configs
```

Response:

```
200 OK

{
  "message": "Retrieved list of files in path defaults/example and scopes",
  "details": {},
  "data": [
    "/defaults/software_a/config.yml",
    "/defaults/software_a/default.yml",
  ]
}
```

## Example - Hostname & Subject ID

Zookeeper structure: same as previous example

Request: 

```
GET /v1/list_files/software_a/configs?hostname=w10dt000001&subject_id=614173'
```

Response:

```
200 OK

{
  "message": "Retrieved list of files in path defaults/example and scopes",
  "details": {},
  "data": [
    "/defaults/software_a/config.yml",
    "/defaults/software_a/default.yml",
    "/computers/w10dt000001/software_a/config.yml",
    "/computers/w10dt000001/software_a/default.yml",
    "/subjects/614173/software_a/config.yml",
    "/subjects/614173/software_a/test.yml",
  ]
}
```
