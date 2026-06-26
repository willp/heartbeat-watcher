# hb-watcher

**HbWatcher** monitors infrastructure health via the `hbserver` Heartbeat API.

## Installation

```bash
pip install hb-watcher
```

This installs:

- the Python package `hb_watcher`
- the CLI command `hbwatcher`

### Systemd install (homelab)

```bash
cp example-hbwatcher_config.json hbwatcher_config.json
nano hbwatcher_config.json
sudo ./install.sh
```

## Configuration

Default config path: `/etc/hbwatcher/hbwatcher_config.json`

```bash
hbwatcher --config /path/to/hbwatcher_config.json
```

See [CONFIG.md](CONFIG.md) for parameter reference.

## Monitoring logs

```bash
sudo journalctl -u hbwatcher -f
```

## Related projects

- `hb-client` (`hb_client`): heartbeat client library and CLI
- `hb-server` (`hb_backend`): API/authentication and key lifecycle services

See [MIGRATION.md](MIGRATION.md) for upgrades from older install paths.

## Uninstallation

```bash
sudo ./uninstall.sh
sudo ./uninstall.sh --purge
```
