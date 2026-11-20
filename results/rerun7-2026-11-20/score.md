# Laws Study Score Report

- **Gate verdict:** `between_validator_branch` (false-block rate 16.1% > 10%)
- **Disagreed double-replays excluded:** 0
- **Wrong changes accepted by `restore`:** 8

## Primary Gate Measures

- **Catch rate (over restore):** 87.5% (7/8) [95% CI 0.0%–100.0%]
- **Same-family catch rate (`moonshotai/Kimi-K3.1-Pro`):** n/a (0/0)
- **False-block rate (incl. incomplete):** 16.1% (5/31) [95% CI 0.0%–50.0%]

## Per-Stage Slipped Wrong Changes

| Stage | Count |
|---|---:|
| `no_law_drafted` | 0 |
| `dropped_by_rules_check` | 0 |
| `dropped_at_approval` | 0 |
| `law_in_force_still_stop` | 1 |

## False-Block Causes

| Cause | Count |
|---|---:|
| `shows_nothing` | 5 |

## All Conditions

| Condition | Catch over restore | Catch all wrong | False block | Incomplete (right) |
|---|---|---|---|---:|
| `ceiling` | 100.0% (8/8) [95% CI 100.0%–100.0%] | 100.0% (11/11) [95% CI 100.0%–100.0%] | 74.2% (23/31) [95% CI 36.7%–97.3%] | 17 |
| `emi_default` | 0.0% (0/8) [95% CI 0.0%–0.0%] | 27.3% (3/11) [95% CI 0.0%–81.8%] | 0.0% (0/31) [95% CI 0.0%–0.0%] | 0 |
| `emi_unapproved_primary` | 87.5% (7/8) [95% CI 0.0%–100.0%] | 90.9% (10/11) [95% CI 50.0%–100.0%] | 16.1% (5/31) [95% CI 0.0%–50.0%] | 0 |
| `emi_unapproved_secondary` | 0.0% (0/8) [95% CI 0.0%–0.0%] | 27.3% (3/11) [95% CI 0.0%–81.8%] | 0.0% (0/31) [95% CI 0.0%–0.0%] | 0 |
| `primary` | 87.5% (7/8) [95% CI 0.0%–100.0%] | 90.9% (10/11) [95% CI 50.0%–100.0%] | 16.1% (5/31) [95% CI 0.0%–50.0%] | 0 |
| `pytest` | 25.0% (2/8) [95% CI 0.0%–100.0%] | 18.2% (2/11) [95% CI 0.0%–66.7%] | 12.9% (4/31) [95% CI 0.0%–44.4%] | 0 |
| `restore` | 0.0% (0/8) [95% CI 0.0%–0.0%] | 27.3% (3/11) [95% CI 0.0%–81.8%] | 0.0% (0/31) [95% CI 0.0%–0.0%] | 0 |
| `restore_laws` | 87.5% (7/8) [95% CI 0.0%–100.0%] | 90.9% (10/11) [95% CI 50.0%–100.0%] | 16.1% (5/31) [95% CI 0.0%–50.0%] | 0 |
