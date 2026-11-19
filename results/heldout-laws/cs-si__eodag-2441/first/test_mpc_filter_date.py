"""Rules for filtering Microsoft Planetary Computer results by date."""
from collections import UserList
from unittest import mock

from eodag.api.product import EOProduct
from eodag.api.provider import ProvidersDict
from eodag.api.search_result import SearchResult
from eodag.config import load_provider_configs
from eodag.crunch import FilterDate
from eodag.plugins.manager import PluginManager
from eodag.plugins.search import PreparedSearch
from eodag.utils import DEFAULT_SHAPELY_GEOMETRY

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
    return SearchResult(UserList(list(result)))


def _ids(products):
    return sorted(p.properties["id"] for p in products)


def test_mpc_results_filtered_by_date_drop_the_later_product():
    """New: filtering the issue's two MPC results between 2021-02-10 and 2021-02-12 drops the 20210214T105131 product and keeps the 20210212T110059 one (A1, A2)."""
    products = _mpc_products()
    filtered = products.crunch(
        FilterDate(dict(start="2021-02-10T00:00:00", end="2021-02-12T00:00:00"))
    )
    assert [p.properties["id"] for p in filtered] == [
        "S2B_MSIL2A_20210212T110059_R094_T30TXP_20210213T073201"
    ]


def test_mpc_results_filtered_over_the_whole_range_keep_both():
    """Guard: filtering the issue's two MPC results over the searched range 2021-02-10 to 2021-02-15 keeps both (A1, A2)."""
    products = _mpc_products()
    filtered = products.crunch(
        FilterDate(dict(start="2021-02-10T00:00:00", end="2021-02-15T00:00:00"))
    )
    assert _ids(filtered) == _ids(products) and len(filtered) == 2


def _product(props):
    properties = {"id": "p", "geometry": DEFAULT_SHAPELY_GEOMETRY}
    properties.update(props)
    return EOProduct(
        provider="fake_provider", properties=properties, collection="fake_collection"
    )


def test_products_with_start_and_end_datetime_still_filter_as_before():
    """Guard: products that do have start_datetime and end_datetime keep being filtered by them (A1, A3)."""
    products = SearchResult(
        UserList(
            [
                _product({"start_datetime": "2025-01-16", "end_datetime": "2025-01-16"}),
                _product({"start_datetime": "2025-01-16", "end_datetime": "2025-01-17"}),
                _product({"start_datetime": "2025-01-17", "end_datetime": "2025-01-18"}),
            ]
        )
    )
    assert len(products.crunch(FilterDate(dict(start="2025-01-16", end="2025-01-17")))) == 2
