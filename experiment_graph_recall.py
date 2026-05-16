"""
对比实验: 纯向量召回 vs 图增强召回
baseline: pgvector cosine top-10 (memory_items)，种子向量 = gm_nodes FTS命中节点的均值
graph:    gm_nodes FTS种子 → PPR 扩展 → 关联 memory_items

策略: Ollama 可能未运行，改用 gm_nodes 里关键词 FTS 找种子节点，
      取其 embedding 均值作为查询向量，对 memory_items 做 cosine 搜索。
      这样 baseline 和 graph 共用同一 embedding 空间，对比公平。
"""

import json
from collections import defaultdict

import psycopg2
import psycopg2.extras

# ─── 配置 ─────────────────────────────────────────────────────────────────────
PG_DSN = "dbname=memu user=postgres password=postgres host=localhost"
USER_ID = "boris"

# 每个查询: (显示名, [关键词列表用于 FTS 找种子节点])
QUERIES = [
    ("量化交易 ShinkaEvolve 选股", ["ShinkaEvolve", "quant", "选股", "量化", "scanner"]),
    ("memU 记忆系统 图增强", ["memU", "graph", "memory", "PPR", "recall"]),
    ("FSC full-self-coding agent", ["FSC", "full-self-coding", "agent", "executor"]),
    ("Gitea 前端美化 液态玻璃", ["Gitea", "液态玻璃", "frontend", "glass", "NAS"]),
    ("SUPER 硬件 H11DSI 内存", ["SUPER", "H11DSI", "hardware", "memory", "512GB"]),
]


# ─── 工具函数 ──────────────────────────────────────────────────────────────────

def vec_literal(v: list[float]) -> str:
    return "[" + ",".join(f"{x:.6f}" for x in v) + "]"


# ─── 从 gm_nodes FTS 找种子，取均值 embedding ──────────────────────────────────

def get_seed_embedding(cur, keywords: list[str]) -> tuple[list[float] | None, list[dict]]:
    """用关键词 ILIKE 从 gm_nodes 找种子节点，返回其 embedding 均值 + 节点列表。"""
    conditions = " OR ".join(["(name ILIKE %s OR description ILIKE %s OR content ILIKE %s)"] * len(keywords))
    params = []
    for kw in keywords:
        params.extend([f"%{kw}%"] * 3)
    params.append(USER_ID)

    cur.execute(
        f"""SELECT id, name, description, embedding::text as emb_text
            FROM gm_nodes
            WHERE ({conditions}) AND user_id = %s AND status = 'active' AND embedding IS NOT NULL
            LIMIT 10""",
        params,
    )
    rows = cur.fetchall()
    if not rows:
        return None, []

    # 解析 embedding 字符串 → float list
    def parse_vec(s: str) -> list[float]:
        return [float(x) for x in s.strip("[]").split(",")]

    vecs = [parse_vec(r["emb_text"]) for r in rows]
    dim = len(vecs[0])
    mean_vec = [sum(v[i] for v in vecs) / len(vecs) for i in range(dim)]
    seeds = [{"id": r["id"], "name": r["name"]} for r in rows]
    return mean_vec, seeds


# ─── Baseline: 直接对 memory_items 做向量搜索 ─────────────────────────────────

def baseline_recall(cur, query_vec: list[float], topk: int = 10) -> list[dict]:
    sql = """
        SELECT id, summary,
               1 - (embedding <=> %s::vector) AS score
        FROM memory_items
        WHERE user_id = %s
          AND embedding IS NOT NULL
        ORDER BY embedding <=> %s::vector
        LIMIT %s
    """
    vlit = vec_literal(query_vec)
    cur.execute(sql, (vlit, USER_ID, vlit, topk))
    rows = cur.fetchall()
    return [{"id": r["id"], "text": r["summary"][:120], "score": float(r["score"])} for r in rows]


# ─── 图增强召回 ────────────────────────────────────────────────────────────────

def graph_recall(cur, query_vec: list[float], topk_seed: int = 5, max_walk: int = 10) -> list[dict]:
    # 1. 向量种子：从 gm_nodes 找最近节点
    sql_seed = """
        SELECT id, name, description, content,
               1 - (embedding <=> %s::vector) AS score
        FROM gm_nodes
        WHERE user_id = %s
          AND status = 'active'
          AND embedding IS NOT NULL
        ORDER BY embedding <=> %s::vector
        LIMIT %s
    """
    vlit = vec_literal(query_vec)
    cur.execute(sql_seed, (vlit, USER_ID, vlit, topk_seed))
    seed_rows = cur.fetchall()
    if not seed_rows:
        return []
    seed_ids = [r["id"] for r in seed_rows]

    # 2. 加载全图 (节点 + 边)
    cur.execute("SELECT id FROM gm_nodes WHERE user_id = %s AND status = 'active'", (USER_ID,))
    all_node_ids = {r["id"] for r in cur.fetchall()}

    cur.execute(
        "SELECT from_id, to_id FROM gm_edges WHERE user_id = %s", (USER_ID,)
    )
    adj: dict[str, set[str]] = defaultdict(set)
    for r in cur.fetchall():
        if r["from_id"] in all_node_ids and r["to_id"] in all_node_ids:
            adj[r["from_id"]].add(r["to_id"])
            adj[r["to_id"]].add(r["from_id"])

    # 3. BFS walk depth=2 从种子出发
    visited = set(seed_ids)
    frontier = set(seed_ids)
    for _ in range(2):
        next_frontier: set[str] = set()
        for nid in frontier:
            next_frontier.update(adj.get(nid, set()) - visited)
        visited.update(next_frontier)
        frontier = next_frontier

    # 4. PPR (simplified) on visited set
    valid_seeds = [s for s in seed_ids if s in all_node_ids]
    if not valid_seeds:
        return []
    tw = 1.0 / len(valid_seeds)
    seed_set = set(valid_seeds)
    rank = {nid: (tw if nid in seed_set else 0.0) for nid in all_node_ids}

    for _ in range(20):
        new_rank = {nid: ((1 - 0.85) * tw if nid in seed_set else 0.0) for nid in all_node_ids}
        for nid in all_node_ids:
            nbrs = adj[nid]
            if not nbrs:
                continue
            contrib = rank[nid] / len(nbrs)
            for nb in nbrs:
                new_rank[nb] = new_rank.get(nb, 0.0) + 0.85 * contrib
        dangling = sum(rank[nid] for nid in all_node_ids if not adj[nid])
        if dangling > 0:
            for sid in valid_seeds:
                new_rank[sid] += 0.85 * dangling * tw
        rank = new_rank

    # 5. 取 visited 中 PPR 最高的节点
    candidate_ids = visited & all_node_ids
    ranked = sorted(candidate_ids, key=lambda n: -rank.get(n, 0.0))[:max_walk]

    # 6. 加载节点内容
    if not ranked:
        return []
    placeholders = ",".join(["%s"] * len(ranked))
    cur.execute(
        f"SELECT id, name, description, content FROM gm_nodes WHERE id IN ({placeholders})",
        ranked,
    )
    node_map = {r["id"]: r for r in cur.fetchall()}

    results = []
    for nid in ranked:
        if nid not in node_map:
            continue
        n = node_map[nid]
        text = f"[{n['name']}] {n['description'] or ''} {n['content'] or ''}".strip()
        results.append({
            "id": nid,
            "name": n["name"],
            "text": text[:120],
            "ppr": round(rank.get(nid, 0.0), 6),
        })
    return results


# ─── 将图节点映射回 memory_items (通过内容相似度 FTS) ─────────────────────────

def find_related_memories(cur, node_names: list[str], topk: int = 5) -> list[dict]:
    """对每个 node name 做全文搜索，找最相关的 memory_items。"""
    if not node_names:
        return []
    combined_query = " ".join(node_names[:5])
    # 用 ts_query 对 memory_items 的 summary 列做简单 LIKE 匹配（避免 FTS 配置依赖）
    conditions = " OR ".join(["summary ILIKE %s"] * min(len(node_names), 5))
    params = [f"%{n}%" for n in node_names[:5]]
    params.append(USER_ID)
    cur.execute(
        f"""SELECT id, summary FROM memory_items
            WHERE ({conditions}) AND user_id = %s
            LIMIT {topk}""",
        params,
    )
    return [{"id": r["id"], "text": r["summary"][:120]} for r in cur.fetchall()]


# ─── 主程序 ────────────────────────────────────────────────────────────────────

def main():
    print(f"连接 PG: {PG_DSN}")
    conn = psycopg2.connect(PG_DSN)
    conn.autocommit = True
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # 注册 vector 类型（pgvector 扩展）
    cur.execute("SELECT NULL::vector")  # 触发类型注册

    print(f"Embedding: gm_nodes 关键词 FTS 种子均值向量\n{'='*70}\n")

    for query_label, keywords in QUERIES:
        print(f"{'='*70}")
        print(f"查询: 【{query_label}】")
        print(f"关键词: {keywords}")
        print(f"{'='*70}")

        print("  → 从 gm_nodes 找种子节点...", end="", flush=True)
        qvec, seed_nodes = get_seed_embedding(cur, keywords)
        if qvec is None:
            print(f" 无命中，跳过")
            continue
        print(f" 命中 {len(seed_nodes)} 个节点: {[n['name'] for n in seed_nodes]}")
        query = query_label

        # Baseline
        base_results = baseline_recall(cur, qvec, topk=10)
        base_ids = {r["id"] for r in base_results}

        # Graph
        graph_results = graph_recall(cur, qvec, topk_seed=5, max_walk=10)
        graph_node_names = [r["name"] for r in graph_results]

        # 图节点关联的 memory_items（通过名称 ILIKE）
        graph_memories = find_related_memories(cur, graph_node_names, topk=10)
        graph_mem_ids = {r["id"] for r in graph_memories}

        # 差集：图带来了哪些 baseline 没有的
        new_ids = graph_mem_ids - base_ids
        overlap_ids = graph_mem_ids & base_ids

        print(f"\n  [BASELINE top-10 memory_items]")
        for i, r in enumerate(base_results, 1):
            print(f"    {i:2}. (score={r['score']:.3f}) {r['text'][:100]}")

        print(f"\n  [GRAPH 激活的节点 (PPR top-10 from gm_nodes)]")
        if graph_results:
            for i, r in enumerate(graph_results, 1):
                print(f"    {i:2}. (ppr={r['ppr']:.5f}) [{r['name']}] {r['text'][:80]}")
        else:
            print("    (无结果)")

        print(f"\n  [GRAPH → 关联 memory_items (共 {len(graph_memories)} 条)]")
        for r in graph_memories:
            marker = "★NEW" if r["id"] in new_ids else "  =="
            print(f"    {marker} {r['text'][:100]}")

        print(f"\n  [差异统计]")
        print(f"    baseline: {len(base_results)} 条")
        print(f"    graph关联memories: {len(graph_memories)} 条")
        print(f"    重叠: {len(overlap_ids)} 条")
        print(f"    图独占新增 (★): {len(new_ids)} 条")

        if new_ids:
            print(f"\n  [图独占新增详情]")
            for r in graph_memories:
                if r["id"] in new_ids:
                    print(f"    → {r['text'][:110]}")

        print()

    cur.close()
    conn.close()
    print("实验完成。")


if __name__ == "__main__":
    main()
