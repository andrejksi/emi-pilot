import json
import networkx as nx

def run_hash(edges, edge_attr=None):
    G = nx.DiGraph()
    for u, v, w in edges:
        G.add_edge(u, v, label=w)
    try:
        return {"returned": nx.weisfeiler_lehman_graph_hash(G, edge_attr=edge_attr)}
    except Exception as exc:
        return {"raised": f"{type(exc).__name__}: {exc}"}

g1 = [(0, 1, "a"), (1, 2, "b")]
g2 = [(1, 0, "a"), (2, 1, "b")]
results = {
    "dir_edge_attr_diff": {"returned": run_hash(g1, "label") != run_hash(g2, "label")},
    "dir_no_edge_attr": {"returned": run_hash(g1, None) != run_hash(g2, None)},
}
print(json.dumps(results, sort_keys=True))
