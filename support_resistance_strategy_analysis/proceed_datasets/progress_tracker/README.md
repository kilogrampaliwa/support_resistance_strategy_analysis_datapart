# ProgressTracker

Tracks processing progress across a batch of items — reports completion percentage, counts of successes/failures/skips, elapsed time, and a live ETA.

---

## Quick Start

```python
from proceed_datasets.progress_tracker.progress_tracker import ProgressTracker

tracker = ProgressTracker(total_items=500, report_interval=10)

for item in items:
    result = process(item)
    tracker.update(success=result.ok, skipped=result.skipped)

summary = tracker.get_summary()
```

---

## Constructor

```python
ProgressTracker(total_items=500, report_interval=10)
```

| Parameter | Description |
|-----------|-------------|
| `total_items` | Total number of items to process |
| `report_interval` | Log progress every N items (default: `10`) |

---

## Methods

### `update(success=True, skipped=False)`

Advances the counter by one and logs progress at every `report_interval` items and on the last item.

```python
tracker.update()                          # success
tracker.update(success=False)             # failure
tracker.update(skipped=True)              # skipped
```

| Parameter | Description |
|-----------|-------------|
| `success` | Mark item as succeeded (default: `True`) |
| `skipped` | Mark item as skipped — takes priority over `success` |

---

### `get_summary()`

Returns a final statistics dictionary. Call after the loop completes.

```python
summary = tracker.get_summary()
```

### Example output

```python
{
    "total_items": 500,
    "processed": 500,
    "succeeded": 478,
    "failed": 12,
    "skipped": 10,
    "elapsed_seconds": 142.3,
    "items_per_second": 3.51,
    "success_rate_pct": 97.5
}
```

| Key | Description |
|-----|-------------|
| `processed` | Items passed to `update()` so far |
| `succeeded` / `failed` / `skipped` | Counts per outcome |
| `elapsed_seconds` | Total wall-clock time since init |
| `items_per_second` | Average throughput |
| `success_rate_pct` | `succeeded / processed × 100` |

---

## Progress Logging

Each automatic report is emitted via `logger.info` in this format:

```
Progress: 100/500 (20.0%) | Succeeded: 96 | Failed: 2 | Elapsed: 0:00:28 | ETA: 0:01:54
```

Reports fire at every `report_interval` items and always on the final item.