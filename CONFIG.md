# HbWatcher Configuration Guide

The `hbwatcher_config.json` file defines how the watcher communicates with your Heartbeat server. All time parameters are in seconds.

## Parameter Reference

| Parameter | Description | Example Value |
| :--- | :--- | :--- |
| `api_url` | **(required)** Base URL of your `hbserver` API. | `"https://hb.example.com:8333/api"` |
| `api_user` | **(required)** Basic Auth username. | `"watcher_admin"` |
| `api_pass` | **(required)** Basic Auth password. | `"super-secret-password"` |
| `ntfy_url` | (Optional) Full URL to your ntfy topic. | `"https://ntfy.sh/my-secret-topic-uuid"` |
| `ntfy_token` | (Optional) Access token for private ntfy servers. | `"tk_123456789"` |
| `deadman_url` | (Optional) URL to ping after each successful loop. | `"https://hc-ping.com/uuid"` |
| `poll_interval` | Seconds between evaluation loops. | `60` |
| `nag_interval` | Seconds before a reminder alert for unacknowledged dead jobs. `0` disables. | `600` |
| `retries` | Retries for failed ntfy notifications. | `3` |
| `delay` | Seconds between retry attempts. | `5` |
| `timeout` | Connection timeout for network requests. | `10` |

## Config file location

Installed systems use `/etc/hbwatcher/hbwatcher_config.json`.

For development, `hbwatcher_config.json` in the working directory is also recognized when present.

## Example template

See `example-hbwatcher_config.json` in the repository root.
