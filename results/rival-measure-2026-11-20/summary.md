# Rival & Alternative Measurement Summary

## Arm `a1` (65 pairs)

- **Reach:** 30/142 functions compared (21.1%); `no_inputs`: 56, `not_checked`: 56
- **Identical-code pairs:** 4
- **Statuses:** `{'agreed': 19, 'disagreed': 6, 'incomplete': 40}`

| Pair Kind | Pairs | Disagreed | Agreed | Incomplete | Tasks Disagreed |
|---|---:|---:|---:|---:|---:|
| `right_vs_right` | 35 | 2 (5.7%) | 18 | 15 | 1/18 (5.6%) |
| `right_vs_wrong` | 21 | 3 (14.3%) | 0 | 18 | 1/7 (14.3%) |
| `wrong_vs_wrong` | 9 | 1 (11.1%) | 1 | 7 | 1/9 (11.1%) |

- **Fork mechanisms:** `{'explicit_raise_vs_value': 20, 'value_diff': 4}`
- **Fork scopes:** `{'interface_fork': 20, 'leaf_fork': 4}`

## Arm `a2` (6 pairs)

- **Reach:** 0/0 functions compared (n/a); `no_inputs`: 0, `not_checked`: 0
- **Identical-code pairs:** 0
- **Statuses:** `{'disagreed': 4, 'incomplete': 2}`

| Pair Kind | Pairs | Disagreed | Agreed | Incomplete | Tasks Disagreed |
|---|---:|---:|---:|---:|---:|
| `alt_vs_right` | 2 | 0 (0.0%) | 0 | 2 | 0/2 (0.0%) |
| `alt_vs_wrong` | 4 | 4 (100.0%) | 0 | 0 | 4/4 (100.0%) |

- **Fork mechanisms:** `{'crash_unintended': 1, 'explicit_raise_vs_value': 2, 'value_diff': 9}`
- **Fork scopes:** `{'interface_fork': 2, 'leaf_fork': 10}`
