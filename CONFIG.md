# ⚙️ HbWatcher Configuration Guide

The `hbwatcher_config.json` file is the brain of the Cardiologist. It defines how the watcher communicates with your Heartbeat server and how it screams for help when things go flatline.  All time-parameters are in units of seconds.


## 📝 Parameter Reference

| Parameter | Description | Example Value |
| :--- | :--- | :--- |
| `api_url` | The base URL of your Heartbeat Django server API. | `"https://hb.example.com:8333/api"` |
| `api_user` | The Basic Auth username configured on your web server. | `"watcher_admin"` |
| `api_pass` | The Basic Auth password for API access. | `"super-secret-password"` |
| `ntfy_url` | The full URL to your ntfy topic (local or public). | `"https://ntfy.sh/my-secret-topic-uuid"` |
| `ntfy_token` | (Optional) Access token for private ntfy servers. | `"tk_123456789"` |
| `deadman_url` | (Optional) A URL to ping (GET) after every successful loop. Use this to monitor the monitor. | `"https://hc-ping.com/uuid"` |
| `poll_interval` | How many seconds to wait between evaluation loops. | `60` |
| `retries` | Number of times to retry a failed ntfy notification. | `3` |
| `delay` | Seconds to wait between retry attempts. | `5` |
| `timeout` | Connection timeout in seconds for all network requests. | `10` |

## Authentication Settings

If you don't use authentication with your **ntfy.sh** server, you can leave out (omit) the `ntfy_token` parameter.

## Deadman URL: Alerting when HbWatcher Dies

You can get free "deadman switch" monitoring from [hc-ping.com](healthchecks.io) which will alert you if HbWatcher stops checking in on a custom, private URL that you can configure on their site.  This helps close the loop on your monitoring so you'll know if your HbWatcher itself is dead.

---

## 📄 Example: Empty Template
Use this template to start a fresh configuration. Save it as `hbwatcher_config.json` in your project root before running `./install.sh`.

```json
{
    "api_url": "",
    "api_user": "",
    "api_pass": "",
    "ntfy_url": "",
    "ntfy_token": "",
    "deadman_url": "",
    "poll_interval": 60,
    "retries": 3,
    "delay": 5,
    "timeout": 10
}
```

# 💡 Configuration Tips
* **Security**: Ensure hbwatcher_config.json is not world-readable. The install.sh script will attempt to place this in /etc/hbwatcher/ with restricted permissions.

*  **The "Watchdog"**: If you use a service like Healthchecks.io, put your unique ping URL into deadman_url. If HbWatcher crashes or the homelab loses internet, that service will alert you that your "Cardiologist" has died.

* **Intervals**: Setting poll_interval lower than 30 seconds may put unnecessary load on your API if you have hundreds of heartbeat entries.
