import pytest

import networkx as nx


def test_capacity_scaling_rejects_unmet_demands_with_zero_capacity():
    """New: capacity_scaling raises NetworkXUnfeasible when the zero-capacity edge cannot meet the demands (A1)."""
    graph = nx.DiGraph()
    graph.add_node(0, demand=1)
    graph.add_node(1, demand=-1)
    graph.add_edge(1, 0, capacity=0, weight=1)

    with pytest.raises(nx.NetworkXUnfeasible):
        nx.capacity_scaling(graph)


def test_capacity_scaling_rejects_unmet_demands_without_edges():
    """New: capacity_scaling raises NetworkXUnfeasible when the graph has demands of 1 and -1 and no edges (A2)."""
    graph = nx.DiGraph()
    graph.add_node(0, demand=1)
    graph.add_node(1, demand=-1)

    with pytest.raises(nx.NetworkXUnfeasible):
        nx.capacity_scaling(graph)


def test_network_simplex_rejects_unmet_demands_with_zero_capacity():
    """Guard: network_simplex raises NetworkXUnfeasible when the zero-capacity edge cannot meet the demands (A3)."""
    graph = nx.DiGraph()
    graph.add_node(0, demand=1)
    graph.add_node(1, demand=-1)
    graph.add_edge(1, 0, capacity=0, weight=1)

    with pytest.raises(nx.NetworkXUnfeasible):
        nx.network_simplex(graph)


def test_min_cost_flow_rejects_unmet_demands_with_zero_capacity():
    """Guard: min_cost_flow raises NetworkXUnfeasible when the zero-capacity edge cannot meet the demands (A3)."""
    graph = nx.DiGraph()
    graph.add_node(0, demand=1)
    graph.add_node(1, demand=-1)
    graph.add_edge(1, 0, capacity=0, weight=1)

    with pytest.raises(nx.NetworkXUnfeasible):
        nx.min_cost_flow(graph)
