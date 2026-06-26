# Migration: hb-watcher naming

## PyPI and CLI

| Before | After |
|--------|-------|
| `hbwatcher.py` (direct script) / `nhbwatcher` | `hbwatcher` |
| (no PyPI package) / `nhbwatcher` | `pip install hb-watcher` |

## Paths

| Before | After |
|--------|-------|
| `/opt/hbwatcher` or `/opt/nhbwatcher` | `/opt/hbwatcher` |
| `/etc/hbwatcher/hbwatcher_config.json` or `/etc/nhbwatcher/...` | `/etc/hbwatcher/hbwatcher_config.json` |

`install.sh` may one-time-copy config from `/etc/nhbwatcher/` when upgrading an intermediate install. The daemon reads only `/etc/hbwatcher/hbwatcher_config.json` at runtime.

## Python imports

```python
from hb_watcher import HbWatcher
```

## Cross-project names

| Role | pip install | CLI | Python import |
|------|-------------|-----|---------------|
| Client | `hb-client` | `hbclient` | `hb_client` |
| Server | `hb-server` | `hbserver` | `hb_backend` |
| Watcher | `hb-watcher` | `hbwatcher` | `hb_watcher` |
