from __future__ import annotations

import ast
import importlib.util
import re
import sys
import tomllib
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SUPPORTED_MEMORIZE_MODALITIES = ("conversation", "document", "image", "audio", "video")
SUPPORTED_MEMORY_TYPES = ("profile", "event", "knowledge", "behavior", "skill", "tool")
SUPPORTED_CLIENT_BACKENDS = {"httpx", "lazyllm_backend", "sdk"}
MIN_PYTHON_VERSION = "3.12"
KEYWORD_ONLY_EXAMPLE_APIS = {
    "clear_memory",
    "create_memory_item",
    "delete_memory_item",
    "list_memory_categories",
    "list_memory_items",
    "memorize",
    "retrieve",
    "update_memory_item",
}


def test_contributing_make_targets_exist() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    docs = [
        ROOT / "README.md",
        ROOT / "CONTRIBUTING.md",
    ]

    targets = {
        match.group(1)
        for match in re.finditer(r"^([A-Za-z0-9_.-]+):(?:\s|$)", makefile, flags=re.MULTILINE)
    }
    referenced_targets = {
        match.group(1)
        for doc in docs
        for match in re.finditer(r"^\s*make\s+([A-Za-z0-9_.-]+)", doc.read_text(encoding="utf-8"), flags=re.MULTILINE)
    }

    missing_targets = sorted(referenced_targets - targets)
    assert not missing_targets, f"Public docs reference unknown make target(s): {missing_targets}"


def test_makefile_status_output_is_ascii_safe() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    unsafe_lines: list[str] = []

    for line_no, line in enumerate(makefile.splitlines(), 1):
        if "@echo" not in line:
            continue
        try:
            line.encode("ascii")
        except UnicodeEncodeError:
            unsafe_lines.append(f"Makefile:{line_no}: {line.strip()}")

    assert not unsafe_lines, f"Makefile status output should be ASCII-safe: {unsafe_lines}"


def test_non_cli_source_modules_do_not_print_to_stdout() -> None:
    stdout_calls: list[str] = []

    for path in sorted((ROOT / "src" / "memu").rglob("*.py")):
        if path.name == "cli.py" or path.stem.endswith("_cli"):
            continue
        module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(module):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print":
                stdout_calls.append(f"{path.relative_to(ROOT)}:{node.lineno}")

    assert not stdout_calls, f"Library modules should use logging instead of print(): {stdout_calls}"


def test_pre_commit_hooks_include_safety_checks() -> None:
    config = (ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")

    assert "https://github.com/pre-commit/pre-commit-hooks" in config
    assert "https://github.com/astral-sh/ruff-pre-commit" in config
    assert "id: check-added-large-files" in config
    assert "args: [--maxkb=1024]" in config
    assert "id: detect-private-key" in config
    assert "id: mixed-line-ending" in config
    assert "args: [--fix=lf]" in config
    assert "id: trailing-whitespace" in config
    assert "id: end-of-file-fixer" in config


def test_issue_templates_route_security_reports_privately() -> None:
    bug_report = (ROOT / ".github" / "ISSUE_TEMPLATE" / "bug_report.yml").read_text(encoding="utf-8")
    issue_config = (ROOT / ".github" / "ISSUE_TEMPLATE" / "config.yml").read_text(encoding="utf-8")

    assert "do not open a public issue" in bug_report
    assert "vulnerability" in bug_report
    assert "leaked credential" in bug_report
    assert "private user data" in bug_report
    assert "https://github.com/NevaMind-AI/MemU/security/policy" in bug_report
    assert "Security Reports" in issue_config
    assert "https://github.com/NevaMind-AI/MemU/security/policy" in issue_config


def test_pull_request_template_matches_project_gates() -> None:
    template = (ROOT / ".github" / "PULL_REQUEST_TEMPLATE.md").read_text(encoding="utf-8")
    pr_title_workflow = (ROOT / ".github" / "workflows" / "pr-title.yml").read_text(encoding="utf-8")

    template.encode("ascii")
    assert "`make check`" in template
    assert "`make test`" in template
    assert "`make docs-build`" in template
    assert "Security or privacy impact" in template
    assert "Public API impact" in template
    assert "Storage/backend impact" in template
    assert "No secrets, credentials, or private user data" in template
    for prefix in ["feat", "fix", "docs", "test", "refactor", "perf", "style", "ci", "build", "chore", "revert"]:
        assert f"`{prefix}`" in template
        assert f"            {prefix}" in pr_title_workflow


def test_repository_markdown_local_links_exist() -> None:
    docs = [
        ROOT / "README.md",
        ROOT / "CONTRIBUTING.md",
        ROOT / "CODE_OF_CONDUCT.md",
        ROOT / "SECURITY.md",
        ROOT / "SUPPORT.md",
        ROOT / ".github" / "PULL_REQUEST_TEMPLATE.md",
        *sorted((ROOT / "readme").rglob("*.md")),
        *sorted((ROOT / "docs").rglob("*.md")),
        *sorted((ROOT / "examples").rglob("*.md")),
    ]
    missing_links: list[str] = []

    for doc in docs:
        text = doc.read_text(encoding="utf-8")
        for raw_link in _iter_local_reference_targets(text):
            target = raw_link.split("#", 1)[0].strip()
            if not target or _is_external_link(target):
                continue

            target_path = (doc.parent / target).resolve()
            if not _is_inside_root(target_path) or not target_path.exists():
                missing_links.append(f"{doc.relative_to(ROOT)} -> {raw_link}")

    assert not missing_links, f"Markdown local links should resolve: {missing_links}"


def test_readme_landing_page_assets_and_language_nav_are_stable() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    architecture = (ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")
    expected_language_links = {
        "English": "readme/README_en.md",
        "中文": "readme/README_zh.md",
        "日本語": "readme/README_ja.md",
        "한국어": "readme/README_ko.md",
        "Español": "readme/README_es.md",
        "Français": "readme/README_fr.md",
    }
    expected_diagrams = [
        "assets/memu-overall-engineering-architecture.png",
        "assets/memu-overall-algorithm-flow.png",
        "assets/memu-self-evolve-architecture.png",
        "assets/memu-self-evolve-algorithm.png",
    ]

    for label, target in expected_language_links.items():
        assert f"[{label}]({target})" in readme
        assert (ROOT / target).exists()

    for target in expected_diagrams:
        asset = ROOT / target
        assert asset.exists()
        assert asset.stat().st_size > 50_000
        assert asset.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
        assert target in readme
        assert f"../{target}" in architecture


def test_open_source_governance_files_are_present() -> None:
    security = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
    support = (ROOT / "SUPPORT.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    contributing = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
    issue_config = (ROOT / ".github" / "ISSUE_TEMPLATE" / "config.yml").read_text(encoding="utf-8")

    assert "contact@nevamind.ai" in security
    assert "Do not open a public GitHub issue" in security
    assert "Supported Versions" in security
    assert "GitHub Discussions" in support
    assert "Security Policy" in support
    assert "](SECURITY.md)" in readme
    assert "](SUPPORT.md)" in readme
    assert "[Security Policy](SECURITY.md)" in contributing
    assert "Security Reports" in issue_config
    assert "https://github.com/NevaMind-AI/MemU/security/policy" in issue_config


def test_public_community_links_are_canonical() -> None:
    core_repository_link_files = _public_markdown_docs()
    discord_link_files = [
        ROOT / "README.md",
        ROOT / "CONTRIBUTING.md",
        ROOT / "SUPPORT.md",
        ROOT / ".github" / "ISSUE_TEMPLATE" / "config.yml",
    ]
    stale_links: list[str] = []

    for path in core_repository_link_files:
        text = path.read_text(encoding="utf-8")
        if re.search(r"github\.com/NevaMind-AI/memU(?=$|[/?#)])", text):
            stale_links.append(f"{path.relative_to(ROOT)} uses non-canonical repository casing")

    for path in discord_link_files:
        text = path.read_text(encoding="utf-8")
        if "discord.gg/memu" in text:
            stale_links.append(f"{path.relative_to(ROOT)} uses stale Discord invite")

    assert not stale_links, f"Use canonical community links: {stale_links}"


def test_project_package_metadata_declares_license() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]

    assert project["license"] == {"file": "LICENSE.txt"}
    assert (ROOT / project["license"]["file"]).exists()
    assert "License :: OSI Approved :: Apache Software License" in project["classifiers"]


def test_uv_lock_tracks_project_version() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    locked_project = next(package for package in lock["package"] if package["name"] == project["name"])

    assert locked_project["source"] == {"editable": "."}
    assert locked_project["version"] == project["version"]


def test_public_version_constant_tracks_project_version() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    module = ast.parse((ROOT / "src" / "memu" / "_version.py").read_text(encoding="utf-8"))
    version = next(
        node.value.value
        for node in module.body
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
        and target.id == "__version__"
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    )

    assert version == project["version"]


def test_langgraph_dependencies_are_optional_and_current() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = pyproject["project"]
    dependencies = set(project["dependencies"])
    langgraph_extra = set(project["optional-dependencies"]["langgraph"])
    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    locked_project = next(package for package in lock["package"] if package["name"] == "memu-py")
    locked_dependencies = {dependency["name"] for dependency in locked_project["dependencies"]}
    locked_requirements = locked_project["metadata"]["requires-dist"]

    assert "langchain-core>=1.2.7" not in dependencies
    assert not any(dep.startswith("langgraph") for dep in dependencies)
    assert langgraph_extra == {"langgraph>=1.0.6", "langchain-core>=1.2.7"}
    assert "langchain-core" not in locked_dependencies
    assert _requirement_specifier(locked_requirements, "langchain-core", extra="langgraph") == ">=1.2.7"
    assert _requirement_specifier(locked_requirements, "langgraph", extra="langgraph") == ">=1.0.6"


def test_langgraph_example_has_actionable_optional_dependency_guard() -> None:
    example = (ROOT / "examples" / "langgraph_demo.py").read_text(encoding="utf-8")

    assert "INSTALL_HINT" in example
    assert "Missing LangGraph dependencies" in example
    assert "pip install 'memu-py[langgraph]'" in example
    assert "uv sync --extra langgraph" in example
    assert "except ModuleNotFoundError as exc" in example
    assert 'if exc.name not in {"langgraph", "langchain_core"}' in example
    assert "raise" in example


def test_langgraph_docs_document_optional_extra_install_paths() -> None:
    docs = (ROOT / "docs" / "langgraph_integration.md").read_text(encoding="utf-8")

    assert 'pip install "memu-py[langgraph]"' in docs
    assert 'uv add "memu-py[langgraph]"' in docs
    assert "uv sync --extra langgraph" in docs


def test_public_docs_use_current_database_environment_names() -> None:
    docs = [
        ROOT / "README.md",
        *sorted((ROOT / "readme").glob("README_*.md")),
        *sorted((ROOT / "docs").rglob("*.md")),
        *sorted((ROOT / "examples").rglob("*.md")),
        *sorted((ROOT / "examples").rglob("*.txt")),
        *sorted((ROOT / "examples").rglob("*.py")),
    ]
    legacy_refs: list[str] = []

    for path in docs:
        text = path.read_text(encoding="utf-8")
        for line_no, line in enumerate(text.splitlines(), 1):
            if "MEMU_DATABASE_URL" in line:
                legacy_refs.append(f"{path.relative_to(ROOT)}:{line_no}: {line.strip()}")

    assert not legacy_refs, f"Use MEMU_DATABASE_DSN instead of legacy MEMU_DATABASE_URL: {legacy_refs}"


def test_public_docs_use_current_provider_environment_names() -> None:
    docs = [
        ROOT / "README.md",
        *sorted((ROOT / "readme").glob("README_*.md")),
        *sorted((ROOT / "docs").rglob("*.md")),
        *sorted((ROOT / "examples").rglob("*.md")),
        *sorted((ROOT / "examples").rglob("*.txt")),
        *sorted((ROOT / "examples").rglob("*.py")),
    ]
    legacy_refs: list[str] = []

    for path in docs:
        text = path.read_text(encoding="utf-8")
        for line_no, line in enumerate(text.splitlines(), 1):
            if "GROK_API_KEY" in line:
                legacy_refs.append(f"{path.relative_to(ROOT)}:{line_no}: {line.strip()}")

    assert not legacy_refs, f"Use XAI_API_KEY for Grok provider defaults: {legacy_refs}"


def test_public_python_config_docs_reference_api_key_environment_names() -> None:
    docs = [
        ROOT / "README.md",
        *sorted((ROOT / "readme").glob("README_*.md")),
        *sorted((ROOT / "docs").rglob("*.md")),
        *sorted((ROOT / "examples").rglob("*.md")),
        *sorted((ROOT / "examples").rglob("*.txt")),
        *sorted((ROOT / "examples").rglob("*.py")),
        *sorted((ROOT / "src").rglob("*.py")),
    ]
    forbidden_fragments = [
        '"api_key": "your_api_key"',
        '"api_key": "your-api-key"',
        '"api_key": "your_voyage_api_key"',
        '"api_key": "your_openrouter_api_key"',
        'api_key="your_api_key"',
        'api_key="your-api-key"',
        'api_key="your_voyage_api_key"',
        'api_key="your_openrouter_api_key"',
        "'api_key': 'your_api_key'",
        "'api_key': 'your-api-key'",
        "'api_key': 'your_voyage_api_key'",
        "'api_key': 'your_openrouter_api_key'",
        "api_key='your_api_key'",
        "api_key='your-api-key'",
        "api_key='your_voyage_api_key'",
        "api_key='your_openrouter_api_key'",
    ]
    stale_refs: list[str] = []

    for path in docs:
        text = path.read_text(encoding="utf-8")
        for line_no, line in enumerate(text.splitlines(), 1):
            for fragment in forbidden_fragments:
                if fragment in line:
                    stale_refs.append(f"{path.relative_to(ROOT)}:{line_no}: {line.strip()}")

    assert not stale_refs, f"Use environment variable names in Python api_key config examples: {stale_refs}"

    for readme_path in [ROOT / "README.md", *sorted((ROOT / "readme").glob("README_*.md"))]:
        readme = readme_path.read_text(encoding="utf-8")
        assert '"api_key": "MEMU_QWEN_API_KEY"' in readme, readme_path.name
        assert '"api_key": "VOYAGE_API_KEY"' in readme, readme_path.name
        assert '"api_key": "OPENROUTER_API_KEY"' in readme, readme_path.name


def test_lazyllm_dependencies_are_optional_and_current() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = pyproject["project"]
    dependencies = set(project["dependencies"])
    lazyllm_extra = set(project["optional-dependencies"]["lazyllm"])
    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    locked_project = next(package for package in lock["package"] if package["name"] == "memu-py")
    locked_dependencies = {dependency["name"] for dependency in locked_project["dependencies"]}
    locked_requirements = locked_project["metadata"]["requires-dist"]

    assert "lazyllm>=0.7.3" not in dependencies
    assert lazyllm_extra == {"lazyllm>=0.7.3"}
    assert "lazyllm" not in locked_dependencies
    assert _requirement_specifier(locked_requirements, "lazyllm", extra="lazyllm") == ">=0.7.3"


def test_claude_dependencies_are_optional_and_current() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = pyproject["project"]
    dependencies = set(project["dependencies"])
    claude_extra = set(project["optional-dependencies"]["claude"])
    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    locked_project = next(package for package in lock["package"] if package["name"] == "memu-py")
    locked_dependencies = {dependency["name"] for dependency in locked_project["dependencies"]}
    locked_requirements = locked_project["metadata"]["requires-dist"]
    proactive_sources = "\n".join(
        path.read_text(encoding="utf-8") for path in sorted((ROOT / "examples" / "proactive").rglob("*.py"))
    )

    assert "claude-agent-sdk>=0.1.24" not in dependencies
    assert claude_extra == {"claude-agent-sdk>=0.1.24"}
    assert "claude-agent-sdk" not in locked_dependencies
    assert _requirement_specifier(locked_requirements, "claude-agent-sdk", extra="claude") == ">=0.1.24"
    assert "aiohttp" not in proactive_sources
    assert "dict[str, any]" not in proactive_sources
    assert "your memu api key" not in proactive_sources


def test_proactive_claude_example_has_actionable_optional_dependency_guard() -> None:
    claude_sdk = (ROOT / "examples" / "proactive" / "memory" / "claude_sdk.py").read_text(encoding="utf-8")

    assert "INSTALL_HINT" in claude_sdk
    assert "The proactive Claude example requires claude-agent-sdk" in claude_sdk
    assert "pip install 'memu-py[claude]'" in claude_sdk
    assert "uv sync --extra claude" in claude_sdk
    assert "except ModuleNotFoundError as exc" in claude_sdk
    assert 'if exc.name != "claude_agent_sdk"' in claude_sdk
    assert "raise SystemExit(INSTALL_HINT) from exc" in claude_sdk


def test_readmes_document_claude_optional_extra_for_proactive_example() -> None:
    readmes = [
        ROOT / "README.md",
        *sorted((ROOT / "readme").glob("README_*.md")),
    ]

    for readme_path in readmes:
        readme = readme_path.read_text(encoding="utf-8")
        assert 'pip install "memu-py[claude]"' in readme, readme_path.name
        assert "uv sync --extra claude" in readme, readme_path.name
        assert 'export OPENAI_API_KEY="..."' in readme, readme_path.name
        assert 'export ANTHROPIC_API_KEY="..."' in readme, readme_path.name
        assert "python proactive.py" in readme, readme_path.name


def test_postgres_optional_dependency_errors_are_actionable() -> None:
    optional_source = (ROOT / "src" / "memu" / "database" / "postgres" / "optional.py").read_text(encoding="utf-8")
    models_source = (ROOT / "src" / "memu" / "database" / "postgres" / "models.py").read_text(encoding="utf-8")
    schema_source = (ROOT / "src" / "memu" / "database" / "postgres" / "schema.py").read_text(encoding="utf-8")

    assert "pip install 'memu-py[postgres]'" in optional_source
    assert "uv sync --extra postgres" in optional_source
    assert "def postgres_extra_import_error" in optional_source
    assert "postgres_extra_import_error() from exc" in models_source
    assert "postgres_extra_import_error() from exc" in schema_source
    assert "pgvector is required for Postgres vector support" not in models_source
    assert "pgvector is required for Postgres vector support" not in schema_source


def test_sqlite_migration_docs_explain_postgres_extra_and_dsn() -> None:
    docs = (ROOT / "docs" / "sqlite.md").read_text(encoding="utf-8")
    migration_section = docs.split("### Import from SQLite to PostgreSQL", 1)[1]

    assert 'pip install "memu-py[postgres]"' in migration_section
    assert "uv sync --extra postgres" in migration_section
    assert "postgresql+psycopg://user:password@host:5432/memu" in migration_section
    assert '"dsn": "postgresql://..."' not in migration_section


def test_sqlite_docs_use_environment_api_key_reference() -> None:
    docs = (ROOT / "docs" / "sqlite.md").read_text(encoding="utf-8")

    assert '"api_key": "your-api-key"' not in docs
    assert "Set `OPENAI_API_KEY` in your environment" in docs
    assert docs.count('"api_key": "OPENAI_API_KEY"') >= 5
    assert "not a literal secret to paste into source code" in docs


def test_proactive_platform_config_uses_environment() -> None:
    module_path = ROOT / "examples" / "proactive" / "memory" / "platform" / "common.py"
    spec = importlib.util.spec_from_file_location("proactive_platform_common", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)

    with patch.dict(
        "os.environ",
        {
            "MEMU_API_KEY": " platform-key ",
            "MEMU_BASE_URL": " https://example.memu.test/ ",
            "MEMU_USER_ID": " user-1 ",
            "MEMU_AGENT_ID": " agent-1 ",
        },
        clear=True,
    ):
        config = module.get_platform_memory_config()

    assert config.api_key == "platform-key"
    assert config.base_url == "https://example.memu.test"
    assert config.user_id == "user-1"
    assert config.agent_id == "agent-1"

    with patch.dict("os.environ", {}, clear=True):
        try:
            module.get_platform_memory_config()
        except ValueError as exc:
            assert "MEMU_API_KEY" in str(exc)
        else:
            raise AssertionError("MEMU_API_KEY should be required for platform proactive memory")


def test_package_declares_pep561_typing_support() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = pyproject["project"]
    maturin = pyproject["tool"]["maturin"]
    manifest = (ROOT / "MANIFEST.in").read_text(encoding="utf-8")

    assert (ROOT / "src" / "memu" / "py.typed").exists()
    assert "Typing :: Typed" in project["classifiers"]
    assert "memu/py.typed" in maturin["include"]
    assert "recursive-include src/memu *.py *.pyi py.typed" in manifest


def test_python_version_floor_is_consistent() -> None:
    pyproject_text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    project = tomllib.loads(pyproject_text)["project"]
    uv_lock = (ROOT / "uv.lock").read_text(encoding="utf-8")
    cargo = (ROOT / "Cargo.toml").read_text(encoding="utf-8")
    build_workflow = (ROOT / ".github" / "workflows" / "build.yml").read_text(encoding="utf-8")
    release_workflow = (ROOT / ".github" / "workflows" / "release-please.yml").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    translated_readmes = [path.read_text(encoding="utf-8") for path in sorted((ROOT / "readme").glob("README_*.md"))]

    assert project["requires-python"] == f">={MIN_PYTHON_VERSION}"
    assert (ROOT / ".python-version").read_text(encoding="utf-8").strip() == MIN_PYTHON_VERSION
    assert f'requires-python = ">={MIN_PYTHON_VERSION}"' in uv_lock
    assert f'python_version = "{MIN_PYTHON_VERSION}"' in pyproject_text
    assert f'target-version = "py{MIN_PYTHON_VERSION.replace(".", "")}"' in pyproject_text
    assert f"Programming Language :: Python :: {MIN_PYTHON_VERSION}" in project["classifiers"]
    assert f"abi3-py{MIN_PYTHON_VERSION.replace('.', '')}" in cargo
    assert f'"{MIN_PYTHON_VERSION}"' in build_workflow
    assert '"3.13"' in build_workflow
    assert f'python-version: "{MIN_PYTHON_VERSION}"' in release_workflow
    assert 'python-version: "3.13"' not in release_workflow
    assert f"python-{MIN_PYTHON_VERSION}+" in readme
    for translated_readme in translated_readmes:
        assert f"python-{MIN_PYTHON_VERSION}+" in translated_readme
        assert f"Python {MIN_PYTHON_VERSION}+" in translated_readme


def test_public_docs_do_not_advertise_old_python_floor() -> None:
    checked_paths = [
        ROOT / "README.md",
        *sorted((ROOT / "readme").glob("README_*.md")),
        *sorted((ROOT / "docs").rglob("*.md")),
        *sorted(path for path in (ROOT / "examples").rglob("*.py") if "resources" not in path.parts),
    ]
    stale_refs: list[str] = []

    for path in checked_paths:
        text = path.read_text(encoding="utf-8")
        for line_no, line in enumerate(text.splitlines(), 1):
            if "Python 3.13+" in line or "python-3.13+" in line:
                stale_refs.append(f"{path.relative_to(ROOT)}:{line_no}: {line.strip()}")

    assert not stale_refs, f"Public docs should advertise Python {MIN_PYTHON_VERSION}+: {stale_refs}"


def test_public_markdown_docs_do_not_contain_mojibake_markers() -> None:
    markers = [
        "馃",
        "鈹",
        "鈻",
        "鈽",
        "鉁",
        "锟",
        "ï¿½",
        "\ufffd",
        "涓枃",
        "鏃ユ湰",
        "頃滉",
        "Espa帽ol",
        "Fran莽ais",
    ]
    checked_paths = [
        ROOT / "README.md",
        *sorted((ROOT / "readme").glob("README_*.md")),
        *sorted((ROOT / "docs").rglob("*.md")),
    ]
    mojibake_hits: list[str] = []

    for path in checked_paths:
        text = path.read_text(encoding="utf-8")
        for line_no, line in enumerate(text.splitlines(), 1):
            found = [marker for marker in markers if marker in line]
            if found:
                mojibake_hits.append(
                    f"{path.relative_to(ROOT)}:{line_no}: markers={found!r} line={line.strip()!r}"
                )

    assert not mojibake_hits, f"Public Markdown docs should be valid UTF-8 text: {mojibake_hits}"


def test_locked_dependencies_do_not_raise_python_floor() -> None:
    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    dependencies_with_higher_floor: list[str] = []

    for package in lock.get("package", []):
        requirement = package.get("requires-python")
        if isinstance(requirement, str) and not _supports_minimum_python(requirement, MIN_PYTHON_VERSION):
            name = package.get("name", "<unknown>")
            version = package.get("version", "<unknown>")
            dependencies_with_higher_floor.append(f"{name}=={version} requires {requirement}")

    assert not dependencies_with_higher_floor, (
        f"Locked dependencies must support Python {MIN_PYTHON_VERSION}+: {dependencies_with_higher_floor}"
    )


def test_packaging_manifest_tracks_current_source_layout() -> None:
    manifest = (ROOT / "MANIFEST.in").read_text(encoding="utf-8")

    assert "include LICENSE.txt" in manifest
    assert "include CODE_OF_CONDUCT.md" in manifest
    assert "include CONTRIBUTING.md" in manifest
    assert "include SECURITY.md" in manifest
    assert "include SUPPORT.md" in manifest
    assert "include mkdocs.yml" in manifest
    assert "recursive-include src/memu *.py *.pyi" in manifest
    assert "recursive-include assets *.png *.gif *.jpg *.jpeg" in manifest
    assert "recursive-include readme *.md" in manifest
    assert "recursive-include examples *.py *.md *.json *.txt *.png *.jpg *.jpeg *.sh .env.example" in manifest
    assert "recursive-include memu *.py" not in manifest
    assert "exclude .env.example" not in manifest


def test_mkdocs_config_points_to_existing_docs() -> None:
    mkdocs = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    missing_docs: list[str] = []

    assert "site_name: memU" in mkdocs
    assert "repo_url: https://github.com/NevaMind-AI/MemU" in mkdocs
    assert "name: material" in mkdocs
    assert "mkdocstrings:" in mkdocs

    for target in _mkdocs_nav_targets(mkdocs):
        target_path = (ROOT / "docs" / target).resolve()
        if not _is_inside_root(target_path) or not target_path.exists():
            missing_docs.append(target)

    assert not missing_docs, f"mkdocs.yml should only reference existing docs: {missing_docs}"


def test_dependabot_tracks_dependency_managers() -> None:
    dependabot = (ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8")

    assert "version: 2" in dependabot
    assert 'package-ecosystem: "uv"' in dependabot
    assert 'package-ecosystem: "cargo"' in dependabot
    assert 'package-ecosystem: "github-actions"' in dependabot
    assert dependabot.count('directory: "/"') == 3
    assert dependabot.count('interval: "weekly"') == 3
    assert 'prefix: "chore(deps)"' in dependabot
    assert 'prefix-development: "chore(deps-dev)"' in dependabot
    assert 'prefix: "ci(deps)"' in dependabot
    assert "open-pull-requests-limit: 5" in dependabot


def test_codeql_workflow_scans_python_and_rust() -> None:
    codeql = (ROOT / ".github" / "workflows" / "codeql.yml").read_text(encoding="utf-8")
    security = (ROOT / "SECURITY.md").read_text(encoding="utf-8")

    assert "name: codeql" in codeql
    assert "push:" in codeql
    assert "pull_request:" in codeql
    assert "schedule:" in codeql
    assert "security-events: write" in codeql
    assert "actions: read" in codeql
    assert "contents: read" in codeql
    assert "language: python" in codeql
    assert "language: rust" in codeql
    assert codeql.count("build-mode: none") == 2
    assert "github/codeql-action/init@v4" in codeql
    assert "github/codeql-action/analyze@v4" in codeql
    assert 'category: "/language:${{ matrix.language }}"' in codeql
    assert "CodeQL for Python and Rust" in security


def test_release_workflow_uses_current_artifact_actions_and_scoped_permissions() -> None:
    release_workflow = (ROOT / ".github" / "workflows" / "release-please.yml").read_text(encoding="utf-8")

    assert "permissions:\n  contents: read" in release_workflow
    assert "concurrency:" in release_workflow
    assert "group: release-please-${{ github.ref }}" in release_workflow
    assert "cancel-in-progress: false" in release_workflow
    assert "release-please:\n    runs-on: ubuntu-latest\n    permissions:" in release_workflow
    assert "contents: write" in release_workflow
    assert "issues: write" in release_workflow
    assert "pull-requests: write" in release_workflow
    assert release_workflow.count("actions/upload-artifact@v7") == 2
    assert "actions/upload-artifact@v6" not in release_workflow
    assert release_workflow.count("actions/download-artifact@v8") == 2
    assert "actions/download-artifact@v7" not in release_workflow
    assert "actions: read" in release_workflow
    assert "id-token: write" in release_workflow
    assert "pypa/gh-action-pypi-publish@release/v1" in release_workflow


def test_project_console_scripts_point_to_existing_functions() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    broken_scripts: list[str] = []

    for script_name, target in project.get("scripts", {}).items():
        module_name, sep, function_name = target.partition(":")
        module_path = ROOT / "src" / Path(*module_name.split(".")).with_suffix(".py")
        if sep != ":" or not function_name:
            broken_scripts.append(f"{script_name}={target} is not module:function")
            continue
        if not module_path.exists():
            broken_scripts.append(f"{script_name}={target} missing {module_path.relative_to(ROOT)}")
            continue
        functions = _module_functions(module_path)
        if function_name not in functions:
            broken_scripts.append(f"{script_name}={target} missing function {function_name}")

    assert not broken_scripts, f"Console scripts must point to existing functions: {broken_scripts}"


def test_installation_docs_use_published_distribution_name() -> None:
    docs = [
        ROOT / "README.md",
        *sorted((ROOT / "readme").glob("README_*.md")),
        ROOT / "docs" / "tutorials" / "getting_started.md",
        ROOT / "docs" / "sealos-devbox-guide.md",
        ROOT / "docs" / "sealos_use_case.md",
    ]
    wrong_distribution_refs: list[str] = []

    for doc in docs:
        text = doc.read_text(encoding="utf-8")
        for line_no, line in enumerate(text.splitlines(), 1):
            if re.search(r"\b(?:pip install|uv add)\s+memu(?!-)\b", line):
                wrong_distribution_refs.append(f"{doc.relative_to(ROOT)}:{line_no}: {line.strip()}")

    requirement_files = sorted((ROOT / "examples").rglob("requirements*.txt"))
    for path in requirement_files:
        text = path.read_text(encoding="utf-8")
        for line_no, line in enumerate(text.splitlines(), 1):
            if re.search(r"^\s*memu(?:\s|[<>=!~]|$)", line):
                wrong_distribution_refs.append(f"{path.relative_to(ROOT)}:{line_no}: {line.strip()}")

    assert not wrong_distribution_refs, f"Use the published memu-py distribution name: {wrong_distribution_refs}"


def test_general_python_examples_are_ascii_safe() -> None:
    unsafe_lines: list[str] = []

    for path in sorted((ROOT / "examples").rglob("*.py")):
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            try:
                line.encode("ascii")
            except UnicodeEncodeError:
                unsafe_lines.append(f"{path.relative_to(ROOT)}:{line_no}: {line.strip()!r}")

    assert not unsafe_lines, f"General-purpose Python examples should be ASCII-safe: {unsafe_lines}"


def test_sealos_use_case_docs_track_demo_status_copy() -> None:
    docs = (ROOT / "docs" / "sealos_use_case.md").read_text(encoding="utf-8")
    example = (ROOT / "examples" / "sealos_support_agent.py").read_text(encoding="utf-8")

    for snippet in (
        "[START] Starting Sealos Support Agent Demo (Offline Mode)",
        "[OK] Environment Check: MemU Library detected.",
        "[OK] Runtime: Sealos Devbox (Python 3.12+)",
        "[DONE] Demo Completed Successfully",
    ):
        assert snippet in docs
        assert snippet in example


def test_readme_quickstart_uses_examples_not_test_modules() -> None:
    checked_readmes = [
        ROOT / "README.md",
        *sorted((ROOT / "readme").glob("README_*.md")),
    ]
    stale_quickstarts: list[str] = []

    for path in checked_readmes:
        readme = path.read_text(encoding="utf-8")
        if "cd tests" in readme:
            stale_quickstarts.append(f"{path.relative_to(ROOT)} uses cd tests")
        if re.search(r"^\s*python\s+test_[A-Za-z0-9_]+\.py\b", readme, flags=re.MULTILINE):
            stale_quickstarts.append(f"{path.relative_to(ROOT)} runs a test module as quickstart")
        if re.search(r"^\s*python\s+tests/test_[A-Za-z0-9_]+\.py\b", readme, flags=re.MULTILINE):
            stale_quickstarts.append(f"{path.relative_to(ROOT)} runs a test module without uv")
        if "python examples/getting_started_robust.py" not in readme:
            stale_quickstarts.append(f"{path.relative_to(ROOT)} does not show the robust getting-started example")

    msg = f"README quickstarts should use public examples, not test modules: {stale_quickstarts}"
    assert not stale_quickstarts, msg


def test_public_docs_reference_existing_test_files() -> None:
    missing_test_refs: list[str] = []

    for path in _public_markdown_docs():
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r"\btests/[A-Za-z0-9_./-]+\.py\b", text):
            target = (ROOT / match.group(0)).resolve()
            if not _is_inside_root(target) or not target.exists():
                line_no = text.count("\n", 0, match.start()) + 1
                missing_test_refs.append(f"{path.relative_to(ROOT)}:{line_no}: {match.group(0)}")

    assert not missing_test_refs, f"Public docs should reference existing tests: {missing_test_refs}"


def test_public_docs_use_uv_for_test_commands() -> None:
    direct_test_commands: list[str] = []

    for path in _public_markdown_docs():
        text = path.read_text(encoding="utf-8")
        for line_no, line in enumerate(text.splitlines(), 1):
            if re.search(r"^\s*python\s+tests/test_[A-Za-z0-9_]+\.py\b", line):
                direct_test_commands.append(f"{path.relative_to(ROOT)}:{line_no}: {line.strip()}")

    assert not direct_test_commands, f"Public docs should run tests via uv pytest: {direct_test_commands}"


def test_postgres_integration_check_is_pytest_collectable_and_opt_in() -> None:
    readmes = [
        ROOT / "README.md",
        *sorted((ROOT / "readme").glob("README_*.md")),
    ]
    source = (ROOT / "tests" / "test_postgres.py").read_text(encoding="utf-8")

    for readme_path in readmes:
        readme = readme_path.read_text(encoding="utf-8")
        assert "uv sync --extra postgres" in readme, readme_path.name
        assert "export MEMU_RUN_POSTGRES_TESTS=1" in readme, readme_path.name
        assert "uv run python -m pytest tests/test_postgres.py" in readme, readme_path.name
    assert "async def test_postgres_full_workflow" in source
    assert 'os.environ.get(RUN_POSTGRES_TESTS_ENV) != "1"' in source
    assert "pytest.skip" in source
    assert 'Path(__file__).resolve().parent / "example" / "example_conversation.json"' in source
    assert 'src_path = str(PROJECT_ROOT / "src")' in source
    assert source.index("from memu import MemoryService") > source.index("async def run_postgres_workflow")
    assert "raise SystemExit(main())" in source


def test_lazyllm_integration_check_is_pytest_collectable_and_opt_in() -> None:
    readmes = [
        ROOT / "README.md",
        *sorted((ROOT / "readme").glob("README_*.md")),
    ]
    source = (ROOT / "tests" / "test_lazyllm.py").read_text(encoding="utf-8")

    for readme_path in readmes:
        readme = readme_path.read_text(encoding="utf-8")
        assert "uv sync --extra lazyllm" in readme, readme_path.name
        assert "export MEMU_QWEN_API_KEY=your_api_key" in readme, readme_path.name
        assert "export MEMU_RUN_LAZYLLM_TESTS=1" in readme, readme_path.name
        assert "uv run python -m pytest tests/test_lazyllm.py" in readme, readme_path.name
    assert "async def test_lazyllm_client" in source
    assert "RUN_LAZYLLM_TESTS_ENV = \"MEMU_RUN_LAZYLLM_TESTS\"" in source
    assert 'os.environ.get(RUN_LAZYLLM_TESTS_ENV) != "1"' in source
    assert "pytest.skip" in source
    assert "async def run_lazyllm_workflow" in source
    assert "PROJECT_ROOT / \"examples\" / \"resources\" / \"images\" / \"image1.png\"" in source
    assert "python tests/test_lazyllm.py" in source


def test_live_llm_storage_checks_are_pytest_collectable_and_opt_in() -> None:
    readmes = [
        ROOT / "README.md",
        *sorted((ROOT / "readme").glob("README_*.md")),
    ]

    for readme_path in readmes:
        readme = readme_path.read_text(encoding="utf-8")
        assert "MEMU_RUN_LIVE_LLM_TESTS=1" in readme, readme_path.name
        assert "tests/test_inmemory.py" in readme, readme_path.name
        assert "tests/test_sqlite.py" in readme, readme_path.name
    for filename, function_name in [
        ("test_inmemory.py", "test_inmemory_full_workflow"),
        ("test_sqlite.py", "test_sqlite_full_workflow"),
    ]:
        source = (ROOT / "tests" / filename).read_text(encoding="utf-8")
        assert f"async def {function_name}" in source
        assert "RUN_LIVE_LLM_TESTS_ENV = \"MEMU_RUN_LIVE_LLM_TESTS\"" in source
        assert 'os.environ.get(RUN_LIVE_LLM_TESTS_ENV) != "1"' in source
        assert "pytest.skip" in source
        assert 'Path(__file__).resolve().parent / "example" / "example_conversation.json"' in source
        assert source.index("from memu import MemoryService") > source.index("async def run_")
        assert "raise SystemExit(main())" in source


def test_openrouter_integration_check_is_pytest_collectable_opt_in_and_non_mutating() -> None:
    source = (ROOT / "tests" / "test_openrouter.py").read_text(encoding="utf-8")

    assert "RUN_OPENROUTER_TESTS_ENV = \"MEMU_RUN_OPENROUTER_TESTS\"" in source
    assert "async def test_openrouter_full_workflow" in source
    assert 'os.environ.get(RUN_OPENROUTER_TESTS_ENV) != "1"' in source
    assert "pytest.skip" in source
    assert "async def run_openrouter_workflow" in source
    assert 'Path(__file__).resolve().parent / "example" / "example_conversation.json"' in source
    assert source.index("from memu import MemoryService") > source.index("async def run_openrouter_workflow")
    assert "openrouter_test_output.json" not in source
    assert "examples/output" not in source
    assert "raise SystemExit(main())" in source


def test_public_openrouter_test_commands_are_explicitly_opt_in() -> None:
    missing_opt_in: list[str] = []

    for path in _public_markdown_docs():
        text = path.read_text(encoding="utf-8")
        if "tests/test_openrouter.py" not in text:
            continue
        if "MEMU_RUN_OPENROUTER_TESTS=1" not in text:
            missing_opt_in.append(str(path.relative_to(ROOT)))

    assert not missing_opt_in, (
        "Public OpenRouter live-test commands should set MEMU_RUN_OPENROUTER_TESTS=1: "
        f"{missing_opt_in}"
    )


def test_build_workflow_runs_for_all_pull_requests() -> None:
    build_workflow = (ROOT / ".github" / "workflows" / "build.yml").read_text(encoding="utf-8")

    assert "pull_request" in build_workflow
    assert "head.repo.full_name" not in build_workflow
    assert "base.repo.full_name" not in build_workflow
    assert "permissions:\n  contents: read" in build_workflow


def test_build_workflow_uses_public_quality_gates() -> None:
    build_workflow = (ROOT / ".github" / "workflows" / "build.yml").read_text(encoding="utf-8")

    assert "run: make check" in build_workflow
    assert "run: make test" in build_workflow
    assert "run: make docs-build" in build_workflow
    assert "uv run make" not in build_workflow
    assert "pre-commit install" not in build_workflow


def test_public_examples_use_real_top_level_exports() -> None:
    exported_names = _top_level_memu_exports()
    checked_files = [
        ROOT / "README.md",
        *sorted((ROOT / "docs").rglob("*.md")),
        *sorted((ROOT / "examples").rglob("*.py")),
    ]
    missing_exports: list[str] = []

    for path in checked_files:
        text = path.read_text(encoding="utf-8")
        imported_names = _memu_imported_names(path, text)
        for imported_name in imported_names:
            if imported_name not in exported_names:
                missing_exports.append(f"{path.relative_to(ROOT)} imports memu.{imported_name}")

    assert not missing_exports, f"Examples and docs should only import public memu exports: {missing_exports}"


def test_app_exports_are_promoted_to_top_level_package() -> None:
    app_exports = _module_all(ROOT / "src" / "memu" / "app" / "__init__.py")
    top_level_exports = _top_level_memu_exports()

    missing_exports = sorted(app_exports - top_level_exports)

    assert not missing_exports, f"memu.app exports should also be available from memu: {missing_exports}"


def test_public_examples_prefer_stable_top_level_imports() -> None:
    top_level_exports = _top_level_memu_exports()
    checked_files = [
        ROOT / "README.md",
        *sorted((ROOT / "docs").rglob("*.md")),
        *sorted((ROOT / "examples").rglob("*.py")),
    ]
    internal_imports: list[str] = []

    for path in checked_files:
        text = path.read_text(encoding="utf-8")
        if path.suffix == ".py":
            internal_imports.extend(_python_promoted_internal_imports(path, text, top_level_exports))
        else:
            internal_imports.extend(_markdown_promoted_internal_imports(path, text, top_level_exports))

    assert not internal_imports, f"Use stable top-level memu imports for public examples: {internal_imports}"


def test_python_examples_call_keyword_only_apis_with_keywords() -> None:
    positional_calls: list[str] = []

    for path in sorted((ROOT / "examples").rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        module = ast.parse(text, filename=str(path))
        for node in ast.walk(module):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in KEYWORD_ONLY_EXAMPLE_APIS
                and node.args
            ):
                positional_calls.append(f"{path.relative_to(ROOT)}:{node.lineno}: {node.func.attr}()")

    assert not positional_calls, f"Use keyword arguments for public example API calls: {positional_calls}"


def test_public_examples_use_configured_memory_service_llm_clients() -> None:
    allowed_direct_sdk_examples = {
        ROOT / "examples" / "test_nebius_provider.py",
    }
    bypasses: list[str] = []

    for path in sorted((ROOT / "examples").rglob("*.py")):
        if path in allowed_direct_sdk_examples:
            continue
        text = path.read_text(encoding="utf-8")
        for line_no, line in enumerate(text.splitlines(), 1):
            if "AsyncOpenAI(" in line or "OpenAI(" in line or "service.llm_config" in line:
                bypasses.append(f"{path.relative_to(ROOT)}:{line_no}: {line.strip()}")

    assert not bypasses, (
        "Public examples should use MemoryService's configured LLM clients "
        f"instead of bypassing profile routing: {bypasses}"
    )


def test_public_docs_do_not_use_legacy_memory_service_constructor_args() -> None:
    legacy_refs: list[str] = []
    checked_paths = [
        ROOT / "README.md",
        *sorted((ROOT / "readme").glob("README_*.md")),
        *sorted((ROOT / "docs").rglob("*.md")),
        *sorted((ROOT / "examples").rglob("*.md")),
        *sorted((ROOT / "examples").rglob("*.txt")),
        *sorted((ROOT / "examples").rglob("*.py")),
    ]

    for path in checked_paths:
        text = path.read_text(encoding="utf-8")
        for line_no, line in enumerate(text.splitlines(), 1):
            if "MemoryService(" in line or "llm_config" in line:
                window = "\n".join(text.splitlines()[max(0, line_no - 1) : line_no + 8])
                if "MemoryService(" in window and "llm_config" in window:
                    legacy_refs.append(f"{path.relative_to(ROOT)}:{line_no}")

    assert not legacy_refs, f"Use MemoryService(llm_profiles=...) instead of llm_config=: {legacy_refs}"


def test_public_direct_retrieve_examples_do_not_use_http_query_shorthand() -> None:
    legacy_refs: list[str] = []
    checked_paths = [
        ROOT / "README.md",
        *sorted((ROOT / "readme").glob("README_*.md")),
        *sorted((ROOT / "docs").rglob("*.md")),
        *sorted((ROOT / "examples").rglob("*.md")),
        *sorted((ROOT / "examples").rglob("*.txt")),
        *sorted((ROOT / "examples").rglob("*.py")),
    ]

    for path in checked_paths:
        lines = path.read_text(encoding="utf-8").splitlines()
        for index, line in enumerate(lines):
            if ".retrieve(" not in line and "retrieve(" not in line:
                continue
            window = "\n".join(lines[index : index + 8])
            if re.search(r"(?<![A-Za-z_])query\s*=", window):
                legacy_refs.append(f"{path.relative_to(ROOT)}:{index + 1}")

    assert not legacy_refs, f"Use retrieve(queries=[...]) for direct Python examples: {legacy_refs}"


def test_low_level_database_builders_are_only_documented_for_migration() -> None:
    allowed_path = ROOT / "docs" / "sqlite.md"
    low_level_refs: list[str] = []
    checked_paths = [
        ROOT / "README.md",
        *sorted((ROOT / "readme").glob("README_*.md")),
        *sorted((ROOT / "docs").rglob("*.md")),
        *sorted((ROOT / "examples").rglob("*.md")),
        *sorted((ROOT / "examples").rglob("*.txt")),
        *sorted((ROOT / "examples").rglob("*.py")),
    ]

    for path in checked_paths:
        text = path.read_text(encoding="utf-8")
        if path == allowed_path:
            continue
        if "build_sqlite_database" in text or "build_postgres_database" in text:
            low_level_refs.append(str(path.relative_to(ROOT)))

    sqlite_docs = allowed_path.read_text(encoding="utf-8")
    assert not low_level_refs, f"Use MemoryService(database_config=...) outside migration docs: {low_level_refs}"
    assert "This migration snippet intentionally uses" in sqlite_docs
    assert "normal application code should continue to use `MemoryService(database_config=...)`" in sqlite_docs


def test_example_text_resources_use_current_public_api_shapes() -> None:
    stale_fragments = [
        "llm_config=",
        "llm_config={",
        '"api_key": "your-api-key"',
        'query="What programming languages does Alex know?"',
        "top_k=5",
        "service.store.categories",
        '"memory_types": ["profile", "knowledge", "custom"]',
    ]
    stale_refs: list[str] = []

    for path in sorted((ROOT / "examples" / "resources").rglob("*.txt")):
        text = path.read_text(encoding="utf-8")
        for fragment in stale_fragments:
            if fragment in text:
                stale_refs.append(f"{path.relative_to(ROOT)}: {fragment}")

    assert not stale_refs, f"Example resources should not teach stale public API shapes: {stale_refs}"

    docs = (ROOT / "examples" / "resources" / "docs" / "doc1.txt").read_text(encoding="utf-8")
    assert "llm_profiles={" in docs
    assert '"api_key": "OPENAI_API_KEY"' in docs
    assert 'queries=["What programming languages does Alex know?"]' in docs
    assert 'where={"user_id": "alex"}' in docs
    assert "await service.list_memory_categories" in docs
    assert '"memory_types": ["profile", "knowledge", "skill"]' in docs


def test_grok_docs_use_current_memory_service_profile_api() -> None:
    provider_docs = (ROOT / "docs" / "providers" / "grok.md").read_text(encoding="utf-8")
    integration_docs = (ROOT / "docs" / "integrations" / "grok.md").read_text(encoding="utf-8")

    for docs in (provider_docs, integration_docs):
        assert "XAI_API_KEY" in docs
        assert "GROK_API_KEY" not in docs
        assert "MemoryService(llm_config=" not in docs
        assert "llm_profiles={" in docs
        assert '"provider": "grok"' in docs
        assert 'api_key="XAI_API_KEY"' in docs

    assert "XAI_API_KEY=xai-YOUR_API_KEY_HERE" in provider_docs
    assert "from memu import LLMConfig" not in integration_docs


def test_getting_started_profile_memory_is_user_scoped() -> None:
    example_path = ROOT / "examples" / "getting_started_robust.py"
    example = example_path.read_text(encoding="utf-8")
    module = ast.parse(example, filename=str(example_path))

    create_calls: list[ast.Call] = []
    retrieve_calls: list[ast.Call] = []
    for node in ast.walk(module):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr == "create_memory_item":
            create_calls.append(node)
        elif node.func.attr == "retrieve":
            retrieve_calls.append(node)

    assert any(_call_has_keyword_value(call, "user", "user_scope") for call in create_calls)
    assert any(_call_has_keyword_value(call, "where", "user_scope") for call in retrieve_calls)

    docs = (ROOT / "docs" / "tutorials" / "getting_started.md").read_text(encoding="utf-8")
    assert 'user_scope = {"user_id": "demo_user"}' in docs
    assert "user=user_scope" in docs
    assert "where=user_scope" in docs


def test_source_checkout_examples_add_src_path_before_memu_imports() -> None:
    checked_files = [
        ROOT / "examples" / "context_harness_demo.py",
        ROOT / "examples" / "example_1_conversation_memory.py",
        ROOT / "examples" / "example_2_skill_extraction.py",
        ROOT / "examples" / "example_3_multimodal_memory.py",
        ROOT / "examples" / "example_4_openrouter_memory.py",
        ROOT / "examples" / "example_5_with_lazyllm_client.py",
        ROOT / "examples" / "getting_started_robust.py",
        ROOT / "examples" / "langgraph_demo.py",
        ROOT / "examples" / "proactive" / "proactive.py",
        ROOT / "examples" / "sealos_support_agent.py",
        ROOT / "examples" / "test_nebius_provider.py",
    ]
    broken_examples: list[str] = []

    for path in checked_files:
        lines = path.read_text(encoding="utf-8").splitlines()
        memu_import_lines = [
            line_no
            for line_no, line in enumerate(lines, 1)
            if re.match(r"\s*(?:from memu\b|import memu\b)", line)
        ]
        if not memu_import_lines:
            continue
        src_insert_lines = [
            line_no
            for line_no, line in enumerate(lines, 1)
            if "sys.path.insert(0" in line and "src" in "\n".join(lines[max(0, line_no - 4) : line_no + 1])
        ]
        file_path_lines = [
            line_no
            for line_no, line in enumerate(lines, 1)
            if "__file__" in line and "src" in "\n".join(lines[line_no - 1 : line_no + 3])
        ]
        if not src_insert_lines or min(src_insert_lines) > min(memu_import_lines):
            broken_examples.append(f"{path.relative_to(ROOT)} imports memu before adding src to sys.path")
        if not file_path_lines:
            broken_examples.append(f"{path.relative_to(ROOT)} should derive src path from __file__")

    assert not broken_examples, f"Examples should run from source checkouts: {broken_examples}"


def test_python_examples_do_not_hardcode_repo_relative_io_paths() -> None:
    repo_relative_paths: list[str] = []

    for path in sorted((ROOT / "examples").rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        module = ast.parse(text, filename=str(path))
        for node in ast.walk(module):
            if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                continue
            if "examples/resources/" in node.value or "examples/output/" in node.value:
                repo_relative_paths.append(f"{path.relative_to(ROOT)}:{node.lineno}: {node.value!r}")

    assert not repo_relative_paths, (
        "Python examples should derive resource/output paths from __file__, "
        f"not the caller's current working directory: {repo_relative_paths}"
    )


def test_public_examples_use_supported_memorize_modalities() -> None:
    unsupported_modalities: list[str] = []

    for path in sorted((ROOT / "examples").rglob("*.py")):
        unsupported_modalities.extend(_unsupported_python_memorize_modalities(path))

    docs = [
        ROOT / "README.md",
        *sorted((ROOT / "docs").rglob("*.md")),
    ]
    for path in docs:
        text = path.read_text(encoding="utf-8")
        for line_no, modality in _markdown_memorize_modalities(text):
            if modality not in SUPPORTED_MEMORIZE_MODALITIES:
                unsupported_modalities.append(f"{path.relative_to(ROOT)}:{line_no}: modality={modality!r}")

    assert not unsupported_modalities, (
        "Public examples should use supported memorize modalities "
        f"{sorted(SUPPORTED_MEMORIZE_MODALITIES)}: {unsupported_modalities}"
    )


def test_public_markdown_retrieve_examples_use_string_content() -> None:
    legacy_query_shapes: list[str] = []
    docs = [
        ROOT / "README.md",
        *sorted((ROOT / "readme").glob("README_*.md")),
        *sorted((ROOT / "docs").rglob("*.md")),
    ]

    for path in docs:
        text = path.read_text(encoding="utf-8")
        for line_no, line in enumerate(text.splitlines(), 1):
            if re.search(r'"content"\s*:\s*\{\s*"text"\s*:', line):
                legacy_query_shapes.append(f"{path.relative_to(ROOT)}:{line_no}")

    assert not legacy_query_shapes, (
        "Public retrieve examples should use the current string content shape "
        "{\"role\": \"user\", \"content\": \"...\"}: "
        f"{legacy_query_shapes}"
    )


def test_readmes_document_python_retrieve_string_query_items() -> None:
    expected = 'queries=["What are their preferences?"]'

    for path in (ROOT / "README.md", ROOT / "readme" / "README_en.md"):
        text = path.read_text(encoding="utf-8")
        assert expected in text
        assert "normalizes it to a user message before retrieval" in text


def test_supported_modalities_match_preprocess_prompts() -> None:
    prompt_keys = _module_dict_literal_keys(ROOT / "src" / "memu" / "prompts" / "preprocess" / "__init__.py", "PROMPTS")

    assert set(SUPPORTED_MEMORIZE_MODALITIES) == prompt_keys


def test_supported_memory_types_match_database_model() -> None:
    memory_types = _module_literal_alias_values(ROOT / "src" / "memu" / "database" / "models.py", "MemoryType")

    assert set(SUPPORTED_MEMORY_TYPES) == memory_types


def test_memorize_config_description_lists_supported_memory_types() -> None:
    settings = (ROOT / "src" / "memu" / "app" / "settings.py").read_text(encoding="utf-8")

    assert "/".join(SUPPORTED_MEMORY_TYPES) in settings


def test_public_docs_do_not_describe_stale_memory_type_count() -> None:
    stale_refs: list[str] = []
    checked_paths = [
        ROOT / "README.md",
        *sorted((ROOT / "readme").glob("README_*.md")),
        *sorted((ROOT / "docs").rglob("*.md")),
    ]

    for path in checked_paths:
        text = path.read_text(encoding="utf-8")
        for line_no, line in enumerate(text.splitlines(), 1):
            if re.search(r"\b(memory_type|memory type|Memory Type).{0,80}\b5 types\b", line):
                stale_refs.append(f"{path.relative_to(ROOT)}:{line_no}: {line.strip()}")

    assert not stale_refs, f"Public docs should describe all supported memory types: {stale_refs}"


def test_public_examples_use_current_category_prompt_key() -> None:
    legacy_prompt_keys: list[str] = []

    for path in sorted((ROOT / "examples").rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        module = ast.parse(text, filename=str(path))
        for node in ast.walk(module):
            if not isinstance(node, ast.Dict):
                continue
            for key in node.keys:
                if isinstance(key, ast.Constant) and key.value == "custom_prompt":
                    legacy_prompt_keys.append(f"{path.relative_to(ROOT)}:{key.lineno}")

    assert not legacy_prompt_keys, (
        "Use CategoryConfig.summary_prompt instead of the legacy custom_prompt key: "
        f"{legacy_prompt_keys}"
    )


def test_public_docs_use_supported_client_backends() -> None:
    unsupported_backends: list[str] = []
    checked_paths = [
        ROOT / "README.md",
        *sorted((ROOT / "readme").glob("README_*.md")),
        *sorted((ROOT / "docs").rglob("*.md")),
        *sorted((ROOT / "examples").rglob("*.py")),
    ]

    for path in checked_paths:
        text = path.read_text(encoding="utf-8")
        for line_no, backend in _client_backend_values(text):
            if backend not in SUPPORTED_CLIENT_BACKENDS:
                unsupported_backends.append(f"{path.relative_to(ROOT)}:{line_no}: client_backend={backend!r}")

    assert not unsupported_backends, (
        f"Use supported client_backend values {sorted(SUPPORTED_CLIENT_BACKENDS)}: {unsupported_backends}"
    )


def _iter_local_reference_targets(text: str) -> list[str]:
    markdown_targets = re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", text)
    html_src_targets = re.findall(r"\bsrc=[\"']([^\"']+)[\"']", text, flags=re.IGNORECASE)
    return [*markdown_targets, *html_src_targets]


def _public_markdown_docs() -> list[Path]:
    return [
        ROOT / "README.md",
        ROOT / "CONTRIBUTING.md",
        ROOT / "CODE_OF_CONDUCT.md",
        ROOT / "SECURITY.md",
        ROOT / "SUPPORT.md",
        ROOT / ".github" / "PULL_REQUEST_TEMPLATE.md",
        *sorted((ROOT / "readme").glob("README_*.md")),
        *sorted((ROOT / "docs").rglob("*.md")),
        *sorted((ROOT / "examples").rglob("*.md")),
    ]


def _mkdocs_nav_targets(mkdocs: str) -> list[str]:
    targets: list[str] = []

    for line in mkdocs.splitlines():
        stripped = line.strip()
        if not stripped.startswith("- ") or ":" not in stripped:
            continue
        target = stripped.split(":", 1)[1].strip().strip("'\"")
        if target.endswith(".md"):
            targets.append(target)

    return targets


def _top_level_memu_exports() -> set[str]:
    return _module_all(ROOT / "src" / "memu" / "__init__.py")


def _module_all(path: Path) -> set[str]:
    module = ast.parse(path.read_text(encoding="utf-8"))
    for node in module.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    value = ast.literal_eval(node.value)
                    return set(value)
    raise AssertionError(f"{path.relative_to(ROOT)} must declare __all__")


def _module_functions(path: Path) -> set[str]:
    module = ast.parse(path.read_text(encoding="utf-8"))
    return {node.name for node in module.body if isinstance(node, ast.FunctionDef)}


def _module_dict_literal_keys(path: Path, name: str) -> set[str]:
    module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in module.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == name:
            value = node.value
        elif isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name for target in node.targets
        ):
            value = node.value
        else:
            continue
        if not isinstance(value, ast.Dict):
            break
        return {
            key.value
            for key in value.keys
            if isinstance(key, ast.Constant) and isinstance(key.value, str)
        }
    raise AssertionError(f"{path.relative_to(ROOT)} should define dict literal {name}")


def _module_literal_alias_values(path: Path, name: str) -> set[str]:
    module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in module.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
            continue
        value = node.value
        if not (
            isinstance(value, ast.Subscript)
            and isinstance(value.value, ast.Name)
            and value.value.id == "Literal"
        ):
            break
        slice_value = value.slice
        literal_items = slice_value.elts if isinstance(slice_value, ast.Tuple) else [slice_value]
        return {
            item.value
            for item in literal_items
            if isinstance(item, ast.Constant) and isinstance(item.value, str)
        }
    raise AssertionError(f"{path.relative_to(ROOT)} should define Literal alias {name}")


def _call_has_keyword_value(call: ast.Call, keyword_name: str, expected_name: str) -> bool:
    for keyword in call.keywords:
        if keyword.arg == keyword_name and isinstance(keyword.value, ast.Name):
            return keyword.value.id == expected_name
    return False


def _memu_imported_names(path: Path, text: str) -> set[str]:
    if path.suffix == ".py":
        return _python_memu_imported_names(path, text)
    return set(re.findall(r"^\s*from\s+memu\s+import\s+([A-Za-z_][A-Za-z0-9_]*)", text, flags=re.MULTILINE))


def _python_memu_imported_names(path: Path, text: str) -> set[str]:
    imported_names: set[str] = set()
    module = ast.parse(text, filename=str(path))
    for node in ast.walk(module):
        if isinstance(node, ast.ImportFrom) and node.module == "memu":
            imported_names.update(alias.name for alias in node.names)
    return imported_names


def _python_promoted_internal_imports(path: Path, text: str, top_level_exports: set[str]) -> list[str]:
    internal_imports: list[str] = []
    module = ast.parse(text, filename=str(path))
    internal_modules = {"memu.app", "memu.app.service", "memu.app.settings"}

    for node in ast.walk(module):
        if not isinstance(node, ast.ImportFrom) or node.module not in internal_modules:
            continue
        imported_names = {alias.name for alias in node.names}
        promoted_names = sorted(imported_names & top_level_exports)
        if promoted_names:
            internal_imports.append(f"{path.relative_to(ROOT)}:{node.lineno}: {', '.join(promoted_names)}")

    return internal_imports


def _markdown_promoted_internal_imports(path: Path, text: str, top_level_exports: set[str]) -> list[str]:
    internal_imports: list[str] = []
    internal_import_pattern = re.compile(
        r"^\s*from\s+memu\.app(?:\.service|\.settings)?\s+import\s+(.+)$",
        flags=re.MULTILINE,
    )

    for match in internal_import_pattern.finditer(text):
        imported_names = set(re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", match.group(1)))
        promoted_names = sorted(imported_names & top_level_exports)
        if promoted_names:
            line_no = text.count("\n", 0, match.start()) + 1
            internal_imports.append(f"{path.relative_to(ROOT)}:{line_no}: {', '.join(promoted_names)}")

    return internal_imports


def _unsupported_python_memorize_modalities(path: Path) -> list[str]:
    unsupported_modalities: list[str] = []
    text = path.read_text(encoding="utf-8")
    module = ast.parse(text, filename=str(path))
    for node in ast.walk(module):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "memorize"
        ):
            continue
        for keyword in node.keywords:
            if keyword.arg != "modality" or not isinstance(keyword.value, ast.Constant):
                continue
            modality = keyword.value.value
            if isinstance(modality, str) and modality not in SUPPORTED_MEMORIZE_MODALITIES:
                unsupported_modalities.append(f"{path.relative_to(ROOT)}:{node.lineno}: modality={modality!r}")
    return unsupported_modalities


def _markdown_memorize_modalities(text: str) -> list[tuple[int, str]]:
    modalities: list[tuple[int, str]] = []
    for line_no, line in enumerate(text.splitlines(), 1):
        for match in re.finditer(r"\bmodality\s*=\s*[\"']([^\"']+)[\"']", line):
            modalities.append((line_no, match.group(1)))
    return modalities


def _client_backend_values(text: str) -> list[tuple[int, str]]:
    values: list[tuple[int, str]] = []
    for line_no, line in enumerate(text.splitlines(), 1):
        for match in re.finditer(r"[\"']client_backend[\"']\s*:\s*[\"']([^\"']+)[\"']", line):
            values.append((line_no, match.group(1)))
    return values


def _requirement_specifier(requirements: list[dict[str, object]], name: str, *, extra: str) -> str | None:
    marker = f"extra == '{extra}'"
    for requirement in requirements:
        if requirement.get("name") == name and requirement.get("marker") == marker:
            value = requirement.get("specifier")
            return value if isinstance(value, str) else None
    return None


def _is_external_link(target: str) -> bool:
    normalized = target.lower()
    return normalized.startswith(("http://", "https://", "mailto:"))


def _is_inside_root(path: Path) -> bool:
    try:
        path.relative_to(ROOT)
    except ValueError:
        return False
    return True


def _supports_minimum_python(requirement: str, minimum: str) -> bool:
    minimum_version = _version_tuple(minimum)
    for match in re.finditer(r"(?:^|,)\s*(>=|>|==|~=)\s*([0-9]+(?:\.[0-9]+)*)", requirement):
        operator = match.group(1)
        version = _version_tuple(match.group(2))
        if operator in {">=", "~="} and version > minimum_version:
            return False
        if operator == ">" and version >= minimum_version:
            return False
        if operator == "==" and version != minimum_version:
            return False
    return True


def _version_tuple(value: str) -> tuple[int, ...]:
    return tuple(int(part) for part in value.split("."))
