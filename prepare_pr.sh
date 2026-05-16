#!/bin/bash
set -e

echo "Starting PR preparation for memU graph-enhanced retrieval..."

git checkout main
git checkout -b feat/graph-enhanced-retrieval
git cherry-pick ac90183 40044e9 2893ed0

./.venv/Scripts/python -m pytest tests/test_graph_store.py -v --tb=short

git push origin feat/graph-enhanced-retrieval

gh pr create --title "feat: graph-enhanced retrieval with PPR and community detection" \
--body "Adds graph-enhanced retrieval that layers a knowledge graph (Personalized PageRank + Label Propagation + community detection) on top of existing vector search for more contextual memory recall. Core changes: GraphStore repository (CRUD + PPR + LPA + dual-path recall), retrieve pipeline WorkflowStep, configurable score fusion (alpha*vector + beta*graph), Alembic migration for gm_* tables. Configuration: New RetrieveGraphConfig (enabled, weight, max_nodes) — disabled by default, zero impact on existing users. Testing: 30 unit tests covering CRUD, PPR, LPA, community merge, score fusion, config validation. Files changed: 12 files, ~1500 lines added. Known limitations (pre-existing): ddl_mode=\"validate\" still runs Alembic upgrade; migration hard-codes user_id scope column. Breaking changes: None — graph retrieval is opt-in." \
--repo NevaMind-AI/memU --head feat/graph-enhanced-retrieval --base main

echo "PR preparation completed successfully."