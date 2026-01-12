# Oracle Database Integration

## Installation

To use the Oracle Database integration, you must have the `oracledb` python driver installed.

```bash
uv add oracledb
```

## Configuration

The connection URI must use the `oracle+oracledb` prefix.

### Format
`oracle+oracledb://<username>:<password>@<host>:<port>/?service_name=<service_name>`

### Example

```python
config = {
    "metadata_store": {
        "dsn": "oracle+oracledb://myuser:mypassword@localhost:1521/?service_name=XE",
        "ddl_mode": "create"
    }
}
```

The system will automatically convert `oracle://` to `oracle+oracledb://` if the simplified prefix is used, but it is recommended to use the full driver prefix.

## Testing

> [!IMPORTANT]
> The integration includes a robust mock test suite that allows validation of the logic without requiring a local Oracle instance.

You can run the unit tests using `pytest`:

```bash
uv run pytest tests/test_oracle_mock.py
```
