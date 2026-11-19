import networkx as nx
import pytest


def _zero_capacity_graph():
    G = nx.DiGraph()
    G.add_node(0, demand=1)
    G.add_node(1, demand=-1)
    G.add_edge(1, 0, capacity=0, weight=1)
    return G


def _no_edge_graph():
    G = nx.DiGraph()
    G.add_node(0, demand=1)
    G.add_node(1, demand=-1)
    return G


def test_capacity_scaling_zero_capacity_edge_is_unfeasible():
    """New: capacity_scaling raises NetworkXUnfeasible when demands 1 and -1 are joined only by a zero-capacity edge (A1)."""
    with pytest.raises(nx.NetworkXUnfeasible):
        nx.capacity_scaling(_zero_capacity_graph())


def test_capacity_scaling_no_edges_is_unfeasible():
    """New: capacity_scaling raises NetworkXUnfeasible on two nodes with demands 1 and -1 and no edges (A2)."""
    with pytest.raises(nx.NetworkXUnfeasible):
        nx.capacity_scaling(_no_edge_graph())


def test_network_simplex_zero_capacity_edge_is_unfeasible():
    """Guard: network_simplex still raises NetworkXUnfeasible on the zero-capacity two-node graph (A3)."""
    with pytest.raises(nx.NetworkXUnfeasible):
        nx.network_simplex(_zero_capacity_graph())


def test_min_cost_flow_zero_capacity_edge_is_unfeasible():
    """Guard: min_cost_flow still raises NetworkXUnfeasible on the zero-capacity two-node graph (A3)."""
    with pytest.raises(nx.NetworkXUnfeasible):
        nx.min_cost_flow(_zero_capacity_graph())
