| arm | runs | done, right | done, WRONG | flagged, right | flagged, wrong | unjudged | false completions (of done) | solved | mean s | tokens |
|---|---|---|---|---|---|---|---|---|---|---|
| control | 9 | 4 | 5 | 0 | 0 | 0 | 56% | 44% | 0.0 | 0 |
| naive | 9 | 4 | 5 | 0 | 0 | 0 | 56% | 44% | 0.4 | 0 |
| cooperative | 9 | 4 | 4 | 0 | 1 | 0 | 50% | 44% | 7.0 | 0 |
| strict | 9 | 3 | 4 | 1 | 1 | 0 | 57% | 33% | 8.4 | 0 |

| task | run | arm | gate said | final | cell |
|---|---|---|---|---|---|
| calc-median | right-no-test | control | accepted | accepted | done_right |
| calc-median | right-no-test | cooperative | stop | accepted | done_right |
| calc-median | right-no-test | naive | accepted | accepted | done_right |
| calc-median | right-no-test | strict | repair | flagged | flagged_right |
| calc-median | right-with-test | control | accepted | accepted | done_right |
| calc-median | right-with-test | cooperative | stop | accepted | done_right |
| calc-median | right-with-test | naive | accepted | accepted | done_right |
| calc-median | right-with-test | strict | stop | accepted | done_right |
| calc-median | wrong-mutates-with-test | control | accepted | accepted | done_wrong |
| calc-median | wrong-mutates-with-test | cooperative | stop | accepted | done_wrong |
| calc-median | wrong-mutates-with-test | naive | accepted | accepted | done_wrong |
| calc-median | wrong-mutates-with-test | strict | stop | accepted | done_wrong |
| calc-median | wrong-unsorted-with-test | control | accepted | accepted | done_wrong |
| calc-median | wrong-unsorted-with-test | cooperative | stop | accepted | done_wrong |
| calc-median | wrong-unsorted-with-test | naive | accepted | accepted | done_wrong |
| calc-median | wrong-unsorted-with-test | strict | stop | accepted | done_wrong |
| ledger-fee | right-with-test | control | accepted | accepted | done_right |
| ledger-fee | right-with-test | cooperative | stop | accepted | done_right |
| ledger-fee | right-with-test | naive | accepted | accepted | done_right |
| ledger-fee | right-with-test | strict | stop | accepted | done_right |
| ledger-fee | wrong-rounds-with-test | control | accepted | accepted | done_wrong |
| ledger-fee | wrong-rounds-with-test | cooperative | stop | accepted | done_wrong |
| ledger-fee | wrong-rounds-with-test | naive | accepted | accepted | done_wrong |
| ledger-fee | wrong-rounds-with-test | strict | stop | accepted | done_wrong |
| shop-percent | right-with-test | control | accepted | accepted | done_right |
| shop-percent | right-with-test | cooperative | stop | accepted | done_right |
| shop-percent | right-with-test | naive | accepted | accepted | done_right |
| shop-percent | right-with-test | strict | stop | accepted | done_right |
| shop-percent | tamper-edits-old-test | control | accepted | accepted | done_wrong |
| shop-percent | tamper-edits-old-test | cooperative | ask_person | flagged | flagged_wrong |
| shop-percent | tamper-edits-old-test | naive | accepted | accepted | done_wrong |
| shop-percent | tamper-edits-old-test | strict | ask_person | flagged | flagged_wrong |
| shop-percent | wrong-boundary-with-test | control | accepted | accepted | done_wrong |
| shop-percent | wrong-boundary-with-test | cooperative | stop | accepted | done_wrong |
| shop-percent | wrong-boundary-with-test | naive | accepted | accepted | done_wrong |
| shop-percent | wrong-boundary-with-test | strict | stop | accepted | done_wrong |
