"""Download each product twice, varying what the server sends; print the request count per variant."""
import io, json, sys, tempfile, zipfile
sys.path[:0] = [".", sys.argv[1]]
import responses
from _eodag_helpers import IDS, PLUGINS, _product, BASE_URL, ZIP_BYTES
from eodag.api.search_result import SearchResult
out = {}
for ext in [".zip", ".tar", ".nc", ".tif", ""]:
    for disposition in (True, False):
        with tempfile.TemporaryDirectory() as d, responses.RequestsMock(assert_all_requests_are_fired=False) as mock:
            for pid in IDS:
                body = ZIP_BYTES if sys.argv[2] == "zip" else b"data" * 10
                headers = {"content-length": str(len(body))}
                if disposition:
                    headers["content-disposition"] = f'attachment; filename="{pid}{ext}"'
                mock.add(responses.GET, BASE_URL.format(pid), body=body, headers=headers)
            plugin = PLUGINS.get_download_plugin(_product(IDS[0]))
            try:
                for _ in range(2):
                    plugin.download_all(SearchResult([_product(p) for p in IDS]), output_dir=d, extract=False)
                out[f"{ext or 'none'} {'named' if disposition else 'unnamed'}"] = len(mock.calls)
            except BaseException as e:
                out[f"{ext or 'none'} {'named' if disposition else 'unnamed'}"] = "raised " + type(e).__name__
print(json.dumps(out))
