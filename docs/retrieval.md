# Host retrieval configuration

Host segment score cutoffs are selected by `MEMU_MEMORY_MODE`. Configure overrides
in `~/.memu/config.env`; process environment variables take precedence.

`<binary> init` and `<binary> config --cloud|--local` add a commented configuration
template once. The template explains the defaults and independent backend
settings; existing overrides and edits to the template are preserved on reruns.
The commands leave threshold assignments commented so Cloud defaults can evolve
with package upgrades and Local users can supply their own calibration.

## Cloud

Cloud retrieval uses the calibrated defaults below. They apply to the Cloud
embedding model used for calibration; a change to that model requires reviewing
the defaults. Users can override individual categories:

```dotenv
MEMU_MEMORY_MODE=cloud
MEMU_CLOUD_RETRIEVE_MIN_SCORE_SHORT=0.55
MEMU_CLOUD_RETRIEVE_MIN_SCORE_LONG=0.60
MEMU_CLOUD_RETRIEVE_MIN_SCORE_EXTRACTED=0.58
```

An unset Cloud category uses its default. Set a category to `-1` to retain all
valid cosine-scored candidates in that category.

## Local

Local retrieval has no default cutoff. Users calibrate their own embedding model
and corpus, then set the corresponding optional variables:

| Category | Variable | Default |
|---|---|---|
| Short | `MEMU_LOCAL_RETRIEVE_MIN_SCORE_SHORT` | Filtering disabled |
| Long | `MEMU_LOCAL_RETRIEVE_MIN_SCORE_LONG` | Filtering disabled |
| Extracted | `MEMU_LOCAL_RETRIEVE_MIN_SCORE_EXTRACTED` | Filtering disabled |

Recalibrate Local thresholds when changing the embedding model. Local and Cloud
settings are independent: changing `MEMU_MEMORY_MODE` selects only that backend's
thresholds.

## Filtering and query categories

Values must be finite numbers between -1 and 1; segments at or above the cutoff
survive. Only files referenced by surviving segments are returned and mirrored.
Resources are scored separately and are unaffected.

`<binary> retrieve` classifies the original query as short below 200 non-whitespace
characters and long otherwise. `--query-kind short|long|extracted` overrides that
classification. The Codex prompt hook passes `extracted` only after successful
query extraction; failures and input-limit fallbacks retain the original prompt's
short/long category. This filtering applies to host adapters, not the Python
`MemoryService.progressive_retrieve` API or the standalone `memu retrieve` command.
