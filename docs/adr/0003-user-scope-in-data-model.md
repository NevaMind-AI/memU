# ADR 0003: Model User Scope as First-Class Fields on Memory Records

- Status: Accepted
- Date: 2026-02-24

## Context

memU retrieval and writes need scoped operation (for example per `user_id`, `agent_id`, or session) for multi-user and multi-agent scenarios.

Keeping scope outside stored records would force ad-hoc filtering logic and weaken data isolation.

## Decision

Embed scope directly into all persisted entities by merging a configurable `UserConfig.model` with core record models.

- Scope fields are part of resource/category/item/relation models
- Repositories accept `user_data` on writes and `where` filters on reads
- API-level `where` filters are validated against configured scope fields before execution

## Consequences

Positive:

- consistent filtering model across memorize/retrieve/CRUD APIs
- backend-independent scoping semantics
- supports multi-tenant and multi-agent patterns without separate storage stacks

Negative:

- schema/model generation complexity increases
- schema and index shape can vary by chosen scope model
- callers must keep `where` and `user` payloads aligned with configured scope fields
