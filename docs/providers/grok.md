# Grok (xAI) Provider

memU supports [Grok](https://grok.x.ai/) (by xAI) as a first-class LLM provider.

## Prerequisites

1.  **Obtain an API Key**:
    *   Sign up at the [xAI Console](https://console.x.ai/).
    *   Create a new API Key.

## Configuration

2.  **Set Environment Variable**:
    Add the following to your `.env` file:

    ```bash
    GROK_API_KEY=xai-...
    ```

3.  **Update Config**:
    In your configuration (e.g., `config.yaml` or when initializing `MemoryService`), set the LLM provider to `grok`.

    Examples:
    *   **YAML Config**:
        ```yaml
        llm:
          default:
            provider: "grok"
        ```

    *   **Python**:
        ```python
        config = LLMConfig(provider="grok")
        ```

### Defaults

When `provider="grok"` is selected, memU automatically uses:
*   **Base URL**: `https://api.x.ai/v1`
*   **Model**: `grok-2-latest`
*   **API Key Env Var**: `GROK_API_KEY`
