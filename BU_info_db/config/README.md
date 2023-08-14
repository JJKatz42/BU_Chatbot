# Getting Started

**Usage:**
```python
import BU_info_db.config as config

# You MUST init the config module before you can call the `get` method
config.init(
    metadata=[
        config.ConfigVarMetadata(
            var_name="STRING_ENV_VAR"
        ),
        config.ConfigVarMetadata(
            var_name="JSON_VAR",
            is_json=True
        ),
        config.ConfigVarMetadata(
            var_name="TRANSFORMED_VAR",
            transformer=lambda x: int(x)
        )
    ]
)

config.get("STRING_ENV_VAR")  # returns raw string value
config.get("JSON_VAR")  # Returns dict or list based on value
config.get("TRANSFORMED_VAR")  # Returns the value of the TRANSFORMED_VAR var with cast to int
config.get("UNKNOWN_VAR")  # Returns None
config.get("UNKNOWN_VAR", 1)  # Returns default value 1
```
