import networkx as nx
import pytest


@pytest.mark.filterwarnings("ignore:The hashes produced for directed graphs changed")
def test_outward_and_inward_labelled_stars_hash_differently():
    """New: with edge_attr="label", the outward star DiGraph([(0, 1), (0, 2)]) and inward star DiGraph([(1, 0), (2, 0)]) get different Weisfeiler-Lehman hashes (A1)."""
    a = nx.DiGraph([(0, 1), (0, 2)])
    b = nx.DiGraph([(1, 0), (2, 0)])
    for graph in [a, b]:
        nx.set_edge_attributes(graph, "e", "label")
    assert nx.weisfeiler_lehman_graph_hash(a, edge_attr="label") != nx.weisfeiler_lehman_graph_hash(b, edge_attr="label")
