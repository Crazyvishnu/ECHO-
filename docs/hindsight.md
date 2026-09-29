# Hindsight integration

The app uses `hindsight-client` with `HINDSIGHT_BASE_URL`, `HINDSIGHT_API_KEY`, and `HINDSIGHT_BANK_ID`.

| Event | Retained content | Context |
| --- | --- | --- |
| Decision analyzed | Decision, assumptions, recommendation | `product decision analysis` |
| Outcome recorded | Actual result, metrics, feedback | `product decision outcome` |
| Lesson extracted | Lesson, evidence, applicability | `validated decision lesson` |

On every analysis, Echo Chamber asks Hindsight for relevant decision context using the current decision text. The response is fed to the recommendation stage and returned as `memory_used` to make its effect visible.
