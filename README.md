# 🩺 HbWatcher (The Cardiologist)

**HbWatcher** is a lightweight, bare-metal Python daemon designed to monitor your infrastructure's health via the Heartbeat API. It performs stateful evaluation of heartbeat entries, manages alerting transitions, and respects maintenance windows to ensure you only get notified when it actually matters.

## 🚀 Features
* **Stateful Alerting:** Transitions through `NORMAL`, `ALERT_SENT`, `ACKNOWLEDGED`, and `SNOOZED` to prevent notification spam.
* **Maintenance Awareness:** Automatically suppresses alerts if a target matches an active Maintenance Window filter.
* **Urgent Notifications:** Dispatches "Urgent" priority alerts to your `ntfy.sh` server (local or public) with custom sirens and tags.
* **Systemd Native:** Designed to run as a robust long-lived daemon with real-time logging to `journald`.
* **Environmentally Friendly:** Uses an isolated Virtual Environment (venv) to respect modern Linux PEP 668 restrictions.

## 🛠️ Tech Stack
* **Language:** Python 3.8+
* **Supervisor:** systemd
* **Alerting:** ntfy.sh (HTTP-based push notifications)
* **Persistence:** JSON-based configuration

## 📦 Installation

### Prerequisites
The watcher requires the Python `venv` module. If you are on a minimal distribution, you may need to install it manually before running the script.

**Check your system:**
The installer will check this for you. If it fails, follow the distro-specific instructions it provides (e.g., `sudo apt install python3-venv`).

### Quick Start
1.  **Clone and Configure:**
    ```bash
    git clone [https://github.com/youruser/hbwatcher.git](https://github.com/youruser/hbwatcher.git)
    cd hbwatcher
    # Create your config from the template
    cp hbwatcher_config.json.example hbwatcher_config.json
    nano hbwatcher_config.json  # Add your API keys and ntfy topic
    ```
2.  **Run Installer:**
    ```bash
    sudo ./install.sh
    ```
    The installer will create `/opt/hbwatcher`, set up the virtual environment, install dependencies, and start the systemd service automatically.

## ⚙️ Configuration

The `hbwatcher_config.json` file is stored in `/etc/hbwatcher/` once installed.

* `api_url`: Your Django Heartbeat API endpoint.
* `ntfy_url`: Your public or local `ntfy` topic (e.g., `https://ntfy.sh/my-secret-topic`).
* `poll_interval`: How often to check for dead heartbeats (default: 60s).

Read more about here about [How to Configure](CONFIG.md) your HbWatcher.

## 📊 Monitoring Logs
Since HbWatcher runs under systemd, its logs are managed by `journald`. You can view them in real-time with:
```bash
sudo journalctl -u hbwatcher -f
```