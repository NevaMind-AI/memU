# Host retrieval configuration

Configure optional host segment score cutoffs in `~/.memu/config.env` for
Local and Cloud results:

```dotenv
# Example calibration for voyage-3.5-lite through NevaToken:
MEMU_RETRIEVE_MIN_SCORE_SHORT=0.55
MEMU_RETRIEVE_MIN_SCORE_LONG=0.60
MEMU_RETRIEVE_MIN_SCORE_EXTRACTED=0.58
```

Unset cutoffs disable filtering for that category. Values must be finite numbers
between -1 and 1; segments at or above the cutoff survive. Only files referenced
by surviving segments are returned and mirrored. Resources are scored separately
and are unaffected. These example values are model/corpus-specific, not defaults;
Cloud users should calibrate against their Cloud results.

`<binary> retrieve` classifies the original query as short below 200 non-whitespace
characters and long otherwise. `--query-kind short|long|extracted` overrides that
classification. The Codex prompt hook passes `extracted` only after successful
query extraction; failures and input-limit fallbacks retain the original prompt's
short/long category. This filtering applies to host adapters, not the Python
`MemoryService.progressive_retrieve` API or the standalone `memu retrieve` command.
