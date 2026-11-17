# Pilot tasks: soundness

Replay runs 44063535976 and 44063542160 (control arm, commit e989fb6),
checked with `harness/check_tasks.py`. robotpy__cxxheaderparser-124 and
-125 are not in the table: their environment did not build (the project's
build asks for a git tag, and the harness's copy has none).

| task | nothing (must fail) | gold-with-tests (must pass) | gold | sound |
|---|---|---|---|---|
| aristanetworks__anta-1250 | False | True | True | yes |
| aristanetworks__anta-1276 | False | True | True | yes |
| berriai__litellm-11964 | False | True | True | yes |
| bluesky__bluesky-1932 | False | True | True | yes |
| conan-io__conan-18444 | False | True | True | yes |
| cs-si__eodag-1717 | False | True | True | yes |
| deshaw__pyflyby-391 | False | True | True | yes |
| googleapis__python-bigquery-2218 | False | True | True | yes |
| huggingface__huggingface_hub-3180 | False | True | True | yes |
| huggingface__huggingface_hub-3200 | False | True | True | yes |
| matchms__matchms-809 | False | True | True | yes |
| matthewwithanm__python-markdownify-230 | False | True | True | yes |
| meltano__sdk-3091 | False | True | True | yes |
| more-itertools__more-itertools-1028 | False | True | True | yes |
| narwhals-dev__narwhals-2864 | False | True | True | yes |
| openmdao__openmdao-3543 | False | True | True | yes |
| pydap__pydap-519 | False | True | True | yes |
| pymc-devs__pymc-7809 | False | True | True | yes |
| pymodbus-dev__pymodbus-2678 | False | False | False | **NO** |
| scrapy__scrapy-6863 | False | False | False | **NO** |
| scrapy__scrapy-6867 | False | False | False | **NO** |
| skrub-data__skrub-1445 | None | None | None | **NO** |
| stanfordnlp__dspy-8432 | False | False | False | **NO** |
| tornadoweb__tornado-3521 | False | True | True | yes |
| trinodb__trino-python-client-564 | False | True | True | yes |
| tweag__fawltydeps-492 | False | True | True | yes |
| tweag__fawltydeps-495 | False | True | True | yes |
| yt-dlp__yt-dlp-13361 | False | True | True | yes |

5 task(s) broken or not judged: fix or drop them before a live run
