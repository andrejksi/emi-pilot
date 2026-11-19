"""Shared setup for the MPC date-filter rules."""
import pytest
import importlib
from collections import UserList
from unittest import mock


def _imp(module, name):
    """Load setup helpers lazily; they are test setup, not what the rules are about."""
    return getattr(importlib.import_module(module), name)


GEOJSON = {
    "type": "Polygon",
    "coordinates": [
        [
            [-0.957, 43.624],
            [-1.214, 43.630],
            [-1.212, 43.686],
            [-0.776, 43.866],
            [-0.957, 43.624],
        ]
    ],
}

MPC_FEATURES = [
    {
        "type": "Feature",
        "id": "S2A_MSIL2A_20210214T105131_R051_T30TXP_20210215T051748",
        "collection": "sentinel-2-l2a",
        "geometry": GEOJSON,
        "properties": {"datetime": "2021-02-14T10:51:31.024000Z"},
        "assets": {},
        "links": [],
    },
    {
        "type": "Feature",
        "id": "S2B_MSIL2A_20210212T110059_R094_T30TXP_20210213T073201",
        "collection": "sentinel-2-l2a",
        "geometry": GEOJSON,
        "properties": {"datetime": "2021-02-12T11:00:59.024000Z"},
        "assets": {},
        "links": [],
    },
]


def _mpc_products():
    ProvidersDict = _imp("eodag.api.provider", "ProvidersDict")
    load_provider_configs = _imp("eodag.config", "load_provider_configs")
    PluginManager = _imp("eodag.plugins.manager", "PluginManager")
    PreparedSearch = _imp("eodag.plugins.search", "PreparedSearch")
    providers = ProvidersDict.from_configs(load_provider_configs())
    manager = PluginManager(providers)
    plugin = next(
        manager.get_search_plugins(collection="S2_MSI_L2A", provider="planetary_computer")
    )
    with mock.patch(
        "eodag.plugins.search.qssearch.StacSearch._request", autospec=True
    ) as mock_request:
        mock_request.return_value.json.return_value = {
            "type": "FeatureCollection",
            "features": MPC_FEATURES,
            "links": [],
        }
        result = plugin.query(
            PreparedSearch(limit=20),
            collection="S2_MSI_L2A",
            start_datetime="2021-02-10T00:00:00",
            end_datetime="2021-02-15T00:00:00",
        )
    SearchResult = _imp("eodag.api.search_result", "SearchResult")
    return SearchResult(UserList(list(result)))


def _product(props):
    EOProduct = _imp("eodag.api.product", "EOProduct")
    geometry = _imp("eodag.utils", "DEFAULT_SHAPELY_GEOMETRY")
    properties = {"id": "p", "geometry": geometry}
    properties.update(props)
    return EOProduct(
        provider="fake_provider", properties=properties, collection="fake_collection"
    )



@pytest.fixture
def mpc_products():
    """The issue's two MPC search results, as eodag products."""
    return _mpc_products()


@pytest.fixture
def make_products():
    """Build a SearchResult from property dicts."""
    SearchResult = _imp("eodag.api.search_result", "SearchResult")
    return lambda props_list: SearchResult(UserList([_product(p) for p in props_list]))
