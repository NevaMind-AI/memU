# 0020: Self-Contained Host Retrieval Hits

## Status

Accepted.

## Context

Host retrieval feeds agent context. Separate segment and file arrays require the agent to resolve source labels before it can interpret an excerpt or read its source. Database and scope metadata also consume bounded hook context.

## Decision

At the shared host presentation boundary, return `hits` and `resources`. Each hit joins matched `text` with its source's `description`, `track`, and mirror `path`, or inline `content` when mirroring is unavailable. Join by the backend's file ID before omitting internal IDs.

A hit's `score` is the segment score; `created_at` and `updated_at` are source-file timestamps. Preserve segment order and missing-source excerpts. Append source-only hits for files without matched segments, using their file score. Resources retain their location, caption, and available score/timestamps.

The backend API remains layered and scope-filtered. Only the host presentation and its consumers change. Emit compact JSON and omit database IDs and scope metadata from agent context.

## Consequences

Agents consume each hit directly. Multiple excerpts from a source repeat source details. Output length still depends on content and hit count; this projection does not guarantee a host-specific maximum. Host CLI consumers must migrate from `segments`/`files` to `hits`.
