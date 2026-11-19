"""Rules for filtering Microsoft Planetary Computer results by date."""
from eodag.plugins.crunch.filter_date import FilterDate


def _ids(products):
    return sorted(p.properties["id"] for p in products)


def test_mpc_results_filtered_by_date_drop_the_later_product(mpc_products):
    """New: filtering the issue's two MPC results between 2021-02-10 and 2021-02-12 drops the 20210214T105131 product and keeps the 20210212T110059 one (A1, A2)."""
    products = mpc_products
    filtered = products.crunch(
        FilterDate(dict(start="2021-02-10T00:00:00", end="2021-02-12T00:00:00"))
    )
    assert [p.properties["id"] for p in filtered] == [
        "S2B_MSIL2A_20210212T110059_R094_T30TXP_20210213T073201"
    ]


def test_mpc_results_filtered_over_the_whole_range_keep_both(mpc_products):
    """Guard: filtering the issue's two MPC results over the searched range 2021-02-10 to 2021-02-15 keeps both (A1, A2)."""
    products = mpc_products
    filtered = products.crunch(
        FilterDate(dict(start="2021-02-10T00:00:00", end="2021-02-15T00:00:00"))
    )
    assert _ids(filtered) == _ids(products) and len(filtered) == 2


def test_products_with_start_and_end_datetime_still_filter_as_before(make_products):
    """Guard: products that do have start_datetime and end_datetime keep being filtered by them (A1, A3)."""
    products = make_products(
        [
            {"start_datetime": "2025-01-16", "end_datetime": "2025-01-16"},
            {"start_datetime": "2025-01-16", "end_datetime": "2025-01-17"},
            {"start_datetime": "2025-01-17", "end_datetime": "2025-01-18"},
        ]
    )
    assert len(products.crunch(FilterDate(dict(start="2025-01-16", end="2025-01-17")))) == 2
