from eodag.api.provider import ProvidersDict
from eodag.api.search_result import RawSearchResult, SearchResult
from eodag.config import load_provider_configs
from eodag.plugins.manager import PluginManager


def test_planetary_computer_filters_the_reported_late_item():
    """New: Date filtering removes the `20210214T105131` product from the reported Microsoft Planetary Computer window. (A1, A2)"""
    providers = ProvidersDict.from_configs(load_provider_configs())
    plugin = next(
        PluginManager(providers).get_search_plugins(provider="planetary_computer")
    )
    first_id = "S2A_MSIL2A_20210214T105131_R051_T30TXP_20210215T051748"
    second_id = "S2B_MSIL2A_20210212T110059_R094_T30TXP_20210213T073201"
    features = RawSearchResult(
        [
            {
                "type": "Feature",
                "id": product_id,
                "collection": "sentinel-2-l2a",
                "geometry": None,
                "properties": {"datetime": timestamp},
                "assets": {},
                "links": [],
            }
            for product_id, timestamp in (
                (first_id, "2021-02-14T10:51:31Z"),
                (second_id, "2021-02-12T11:00:59Z"),
            )
        ]
    )
    results = SearchResult(plugin.normalize_results(features, collection="S2_MSI_L2A"))
    assert {product.properties["id"] for product in results} == {first_id, second_id}
    assert first_id not in {
        product.properties["id"]
        for product in results.filter_date("2021-02-10T00:00:00", "2021-02-12T00:00:00")
    }
    assert {
        product.properties["id"]
        for product in results.filter_date("2021-02-10T00:00:00", "2021-02-15T00:00:00")
    } == {first_id, second_id}
