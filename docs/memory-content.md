# Writing User Memory for Long-Term Companionship

[简体中文](memory-content.zh.md)

Memory should help a future agent understand a particular person: their experiences, interests, reasons, relationships, collaboration preferences, and project goals. The external agent selects and writes this background; `MemoryService` remains embedding-only.

The embedded memory-job prompt is in [`instructions.py`](../src/memu/hosts/bridging/instructions.py). This guide describes the intended content standard and how to review its output.

## Select grounded background

Keep meaningful details, including significant one-time experiences. A useful memory need not describe a permanent habit. Preserve the scope, frequency, uncertainty, and conditions supported by the evidence.

Separate user statements, explicitly adopted suggestions, and assistant interpretations. An acknowledgement is not necessarily adoption. Keep plans as plans; do not turn self-reported experiences into diagnoses or personality labels. Treat existing summaries as evidence to examine, not verified quotations.

Installation steps, debugging transcripts, command output, version snapshots, acceptance counts, and individual commit histories generally belong in operational records. Mixed conversations can still contain useful personal background. Extract that background without keeping the operational sequence or inferring a character trait from ordinary task requirements.

Requests about the current reply or task normally stay in the conversation. An ongoing project can warrant a concise account of its purpose and the user's goal; an open design-option list alone usually does not. No change is a valid result.

## Reconcile before adding

Read related memories first. Reuse the existing topic when updating information; avoid duplicate facts and translated copies. An explicit correction should update both description and body while preserving unaffected useful facts. Keep context-dependent differences instead of forcing one universal preference. Recency alone does not resolve ambiguous evidence.

An unadopted suggestion usually contributes no user fact. An explicit rejection can be useful when it establishes an ongoing boundary or reason. Record the supported boundary rather than a history of proposed alternatives.

## Write independently readable units

Each unit should identify its subject, meaning, necessary context, and qualifications on one physical line. Use prose or bullets, with optional blank lines; avoid Markdown tables and visual line wrapping. Keep names, reasons, and meaningful detail. A generic category such as "likes games" can erase what made the memory useful.

Descriptions must accurately summarize the body. Dates belong where they establish validity, scope, or a meaningful historical event; this guide does not define a timestamp schema. Keep review commentary outside the prose unless the uncertainty changes the fact's meaning.

Use one English instruction text with the output language specified separately. Where a run specifies no language, follow the source language and preserve names and identifiers. Existing mixed-language memories need not be translated into duplicates. Cross-language retrieval quality depends on the embedding model and needs its own evaluation.

Write background as facts about the user. Historical approvals do not authorize future actions. Rules that must always execute belong in reliably loaded project instructions rather than depending on a retrieval hit.

## Review examples

The following examples are synthetic and illustrate the standard; they are not records of a real user's life or measured model outputs.

| Evidence | Candidate memory | Review reason |
| --- | --- | --- |
| "On quiet evenings I like low-pressure puzzle games because I can pause them. Today I want something harder." | "On quiet evenings, the user likes low-pressure puzzle games because they can pause them." | Preserve the reason and condition; today's request does not establish a recurring preference for harder games. |
| "I reread the essay about the author's return home because it helps me think about leaving my own hometown." | "The user rereads the essay about the author's return home because it helps them reflect on leaving their own hometown." | Preserve the reading experience and personal connection, rather than just recording a title. |
| "My graduation photo matters to me because my mother travelled a long way to be there." | "The user's graduation photo is important to them because their mother travelled a long way to attend." | A meaningful one-time experience is worth retaining without inferring a photography habit. |
| Assistant proposes a weekly call; user says, "Yes, I plan to call my father on Sundays to stay in touch." | "The user plans to call their father on Sundays to stay in touch." | Explicit adoption supports a plan, not proof that the calls already happen. |
| "For research reports, keep evidence and uncertainty clear. This PR reply can be three lines." | "The user wants research reports to make evidence and uncertainty clear." | Keep the preference with its stated task family; the current reply's length limit stays local. |
| "I'm building a garden diary to connect plant photos with what I learn each season. The upload bug is fixed; 42 tests passed." | "The user is building a garden diary to connect plant photos with what they learn each season." | Retain project identity and purpose; leave repair and acceptance history in the work record. |

When correcting an existing memory, review the complete result. If "always wants Chinese PRs" is corrected to "use the issue's language," update that claim and its description while retaining independently supported preferences about repository templates and concise writing.

## Template delivery

Prepare resolves memory-job templates in this order: remote, last-good cache, embedded. Remote refresh has a persistent cooldown. Updating the embedded prompt changes the fallback; an existing remote or cached template can still take precedence. Changing this file does not publish the remote template or replace users' caches.

For a reproducible local evaluation, set `MEMU_TEMPLATE_BASE_URL` to an empty string in an isolated process and use an isolated template-cache directory or temporary home. Disabling remote fetch alone does not discard a last-good cache. Capture the actual rendered job, selected model, source input, and unedited output.

The shared renderer appends the empty-memory submission contract regardless of the selected template. Intentional clearing through Markdown requires `empty: true` and a blank body; writing a non-empty body restores ordinary submission. See [ADR 0025](adr/0025-explicit-empty-memory-markdown.md).

## Validation limits

Template formatting, correct placeholders, complete physical lines, and passing host tests establish structural compatibility. They do not establish faithful extraction or useful recall. Exploratory extraction work informed these rules, but it is not a general quality guarantee.

Evaluate old and new prompts on the same conversations and model, retaining raw inputs and outputs in an authorized location. Review every claim for source support, missed meaningful details, scope expansion, adoption, corrections, and unaffected facts. Include pure operational sessions, important one-time experiences, uncertain statements, and cases that should produce no changes. Use held-out conversations and independent review when possible.

Evaluate retrieval and final answers separately. Fewer lines, smaller files, or a high retrieval hit rate alone do not show that a future answer improves. Real host file access, rendered-template selection, multilingual retrieval, and response usefulness require their own checks.
