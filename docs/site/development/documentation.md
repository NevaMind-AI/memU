# Writing documentation

## Run the site locally

From the repository root, use Node.js 22.12+ and pnpm 11.15.1 (the version in `docs/package.json`):

```sh
pnpm --dir docs install --frozen-lockfile
pnpm --dir docs dev
```

Open the localhost URL printed by VitePress. To inspect a production build:

```sh
pnpm --dir docs build
pnpm --dir docs preview
```

The generated site is `docs/.vitepress/dist/`. Local development and preview require no GitHub Pages permissions.

## Python development

For source development, run commands from the repository root through uv:

```sh
uv sync --python 3.13
uv run pre-commit install
uv run memu-pi --help
uv run python -m pytest tests/test_agentic.py
```

`uv sync` prepares the project `.venv`; `uv run` uses that environment and the checked-out source. The tool installation in the getting-started guide is for everyday CLI use. The site itself uses pnpm as described above.

## Where a change belongs

| Content | Location |
| --- | --- |
| Project introduction, shortest setup path, documentation links | Root `README.md` |
| Installation and everyday usage | `docs/site/guide/` |
| Host integration and limitations | `docs/site/hosts/` |
| CLI, configuration, API contracts, storage options | `docs/site/reference/` |
| Diagnosis and reusable fixes | `docs/site/troubleshooting/` |
| Development workflow and current architecture | `docs/site/development/` |
| Architectural decisions and their context | Existing `docs/adr/` |
| Version summaries | Existing root `CHANGELOG.md` and releases |
| Community task scope and acceptance | Existing `docs/community/` |

For example, a new environment variable belongs in the configuration reference; a pi retrieval change belongs in the host guide; an architectural decision needs an ADR and an updated description of current behavior.

## Update both languages

The English site starts at `docs/site/`; Chinese pages mirror the paths under `docs/site/zh/`. Update both pages in the same change and keep examples, scope, and acceptance criteria aligned. Use explicit matching heading IDs when a translated section needs a stable shared anchor.

Keep internal links relative and point to Markdown sources. Add new pages to the matching sidebar in `docs/.vitepress/config.ts`. The build checks page links; leave broken-link errors enabled. Local search indexes the site content automatically.

## Reuse existing sources

Host installation, task, and uninstall guides remain under `src/memu/hosts/<host>/` because the CLI loads them as package resources. Update those sources when installation behavior changes; the website should explain the entry point and link to the CLI guide rather than duplicate the complete procedure.

The site source directory is intentionally `docs/site/`. Existing ADRs and community tasks remain at their established paths and are linked through the repository. They are not copied into the site. ADRs describe historical decisions; verify current behavior against implementation. Research notes outside the site directory are not published by the site build.

The existing `docs/sqlite.md` contains legacy examples. Use the [current configuration](../reference/configuration.md) and [MemoryService](../reference/service.md) pages for the supported constructor and storage setup.

## Before submitting

1. Update the page that owns the behavior and its translation.
2. Run `pnpm --dir docs build` and inspect the changed pages with preview.
3. Verify commands against the installed CLI and check code examples against implementation. A successful site build does not execute examples.
4. In the PR, list the updated documentation, or explain why documentation is unaffected. Use the existing release process for version summaries.
