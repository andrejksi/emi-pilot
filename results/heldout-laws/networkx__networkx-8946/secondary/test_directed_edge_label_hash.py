import pytest

from networkx import DiGraph, set_edge_attributes, weisfeiler_lehman_graph_hash


@pytest.mark.filterwarnings("ignore:The hashes produced for directed graphs changed:UserWarning")
def test_inward_and_outward_stars_with_edge_labels_have_different_hashes():
    """New: An outward star and an inward star with identical edge labels get different hashes when the labels are used (A1)."""
    outward_star = DiGraph([(0, 1), (0, 2)])
    inward_star = DiGraph([(1, 0), (2, 0)])
    for star in (outward_star, inward_star):
        set_edge_attributes(star, "e", "label")

    assert weisfeiler_lehman_graph_hash(
        outward_star, edge_attr="label"
    ) != weisfeiler_lehman_graph_hash(inward_star, edge_attr="label")
