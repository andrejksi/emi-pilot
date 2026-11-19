import os
import tempfile
from unittest import mock

import pytest

from eodag import EODataAccessGateway
from eodag.api.search_result import SearchResult
from tests.utils import write_eodag_conf_with_fake_credentials


@pytest.fixture(scope="module")
def dag():
    tmp = tempfile.mkdtemp()
    conf_dir = os.path.join(tmp, ".config", "eodag")
    os.makedirs(conf_dir, exist_ok=True)
    write_eodag_conf_with_fake_credentials(os.path.join(conf_dir, "eodag.yml"))
    with mock.patch("os.path.expanduser", return_value=tmp):
        yield EODataAccessGateway()


def _search(dag, start, end):
    with mock.patch.object(
        EODataAccessGateway, "_do_search", return_value=SearchResult([])
    ) as do_search:
        try:
            result = dag.search(
                collection="S2_MSI_L1C", provider="cop_dataspace", start=start, end=end
            )
        except Exception:
            result = None
    return result, do_search


def test_an_impossible_end_date_is_not_sent_to_the_provider(dag):
    """New: a search on S2_MSI_L1C from "2020-01-01" to "2023-11-31" is refused before any query is sent to the provider (A1, A2)."""
    result, do_search = _search(dag, "2020-01-01", "2023-11-31")
    assert (result is None or len(result) == 0, do_search.call_count) == (True, 0)


def test_an_impossible_start_date_is_not_sent_to_the_provider(dag):
    """New: a search with the impossible start date "2023-11-31" is refused before any query is sent to the provider (A1, A2)."""
    result, do_search = _search(dag, "2023-11-31", "2023-12-15")
    assert (result is None or len(result) == 0, do_search.call_count) == (True, 0)


def test_valid_dates_are_still_sent_to_the_provider(dag):
    """Guard: a search on S2_MSI_L1C from "2020-01-01" to "2023-11-30" is still sent to the provider (A3)."""
    result, do_search = _search(dag, "2020-01-01", "2023-11-30")
    assert (result is not None, do_search.call_count) == (True, 1)
