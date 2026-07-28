# Confierge

Simple client for fetching/posting configs to the Ficus API server. Client provides the following additional features:

- provides validation when given a pydantic model
- caching fetched configs locally
- falling back to cached version on fetching and validation failures

### Example

```python
from confierge import Confierge, cache_dir
from pydantic_settings import BaseSettings

class MyConfigModel(BaseSettings):
    param1: str
    param2: int

client = Confierge(ficus_url, cache_dir=cache_dir("my_app", "my_organization"))
config = client.get_config_safe("my_app", model=MyConfigModel)"

# Alternately, with a more specific scope:
client.get_config_safe(
    "my_app",
    mode="high_freq",
    scopes={"hostname": os.getenv("COMPUTERNAME", "unknown")},
    model=MyConfigModel
)
```

## Caching Behavior


``_get_cache``:

1. read cache from file
2. error if missing

``_expire_cache``:

1. backdate existing cache (prefix with timestamp)

``_save_cache``:

1. check if data is identical as cache, if identical skip
2. call expire_cache 
3. save file (see filename convention)


### Cache Naming Convention

Cache file: 

``<namespace>_<scope1>-<identifier1>_<filename>.json``

Backdated: 

``<timestamp>_<namespace>_<scope1>-<identifier1>_<filename>.json``