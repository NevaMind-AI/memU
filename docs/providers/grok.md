# Grok (xAI) Provider

memU includes first-class support for [Grok](https://grok.x.ai/), allowing you to leverage xAI's powerful language models directly within your application.

## Prerequisites

To use this provider, you must have an active xAI account.

1.  Navigate to the [xAI Console](https://console.x.ai/).
2.  Sign up or log in.
3.  Create a new **API Key** in the API Keys section.

## Configuration

The integration is designed to work out-of-the-box with minimal configuration.

### Environment Variables

Set the following environment variable in your `.env` file or system environment:

```bash
XAI_API_KEY=xai-YOUR_API_KEY_HERE
```

### Defaults

When you select the `grok` provider, memU automatically configures the following defaults:

*   **Base URL**: `https://api.x.ai/v1`
*   **Model**: `grok-2-latest`

## Usage Example

You can enable the Grok provider by setting the `provider` field to `"grok"` in your application configuration.

### Using Python Configuration

```python
from memu import MemoryService

# Initialize the service
service = MemoryService(
    llm_profiles={
        "default": {
            "provider": "grok",
            # Defaults: api_key="XAI_API_KEY", base_url="https://api.x.ai/v1",
            # chat_model="grok-2-latest"
        }
    }
)
```

## Troubleshooting

### Connection Issues
If you are unable to connect to the xAI API:
1.  Verify that your `XAI_API_KEY` is set correctly and has not expired.
2.  Ensure that the `base_url` is resolving to `https://api.x.ai/v1`. If you have manual overrides in your settings, they might be conflicting with the default.

### Model Availability
If you receive a `404` or "Model not found" error, xAI may have updated their model names. You can override the model manually in the config if needed:

```python
service = MemoryService(
    llm_profiles={
        "default": {
            "provider": "grok",
            "chat_model": "grok-beta",  # Example override
        }
    }
)
```
