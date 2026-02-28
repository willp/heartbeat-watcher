#!/usr/bin/python3 -u
import os
import sys
import time
import json
import requests
from datetime import datetime, timezone

class HbWatcher:
    def __init__(self, config_path="hbwatcher_config.json"):
        self.config_path = config_path
        
        # Configuration variables (strongly typed/explicit, no dict passing)
        self.api_url = ""
        self.api_user = ""
        self.api_pass = ""
        self.deadman_url = ""
        
        # Operational tuning variables (will be overridden by config if present)
        self.retries = 3
        self.delay = 5
        self.timeout = 10
        self.poll_interval = 60

    def load_config(self):
        """Loads and validates the JSON configuration file."""
        if not os.path.exists(self.config_path):
            print(f"FATAL: Configuration file '{self.config_path}' not found.")
            sys.exit(1)
            
        with open(self.config_path, 'r') as f:
            try:
                cfg = json.load(f)
            except json.JSONDecodeError as e:
                print(f"FATAL: Invalid JSON in '{self.config_path}': {e}")
                sys.exit(1)

        # 1. Enforce required parameters (No hardcoded defaults for auth/URLs)
        try:
            self.api_url = cfg["api_url"]
            self.api_user = cfg["api_user"]
            self.api_pass = cfg["api_pass"]
            self.deadman_url = cfg["deadman_url"]
        except KeyError as e:
            print(f"FATAL: Missing required config parameter: {e}")
            sys.exit(1)

        # 2. Load operational parameters (fallback to class defaults if missing)
        self.retries = cfg.get("retries", self.retries)
        self.delay = cfg.get("delay", self.delay)
        self.timeout = cfg.get("timeout", self.timeout)
        self.poll_interval = cfg.get("poll_interval", self.poll_interval)
        
        print(f"🔧 Config loaded successfully. Polling {self.api_url} every {self.poll_interval}s.")

    def fetch_data_with_retries(self):
        """Fetches data with strict timeouts and a '3 strikes' retry rule."""
        for attempt in range(1, self.retries + 1):
            try:
                response = requests.get(
                    self.api_url, 
                    auth=(self.api_user, self.api_pass), 
                    timeout=self.timeout
                )
                response.raise_for_status() 
                return response.json()
            except requests.exceptions.RequestException as e:
                print(f"⚠️ API Attempt {attempt} failed: {e}")
                if attempt == self.retries:
                    raise # Bubble up the exception on the final strike
                time.sleep(self.delay)

    def dispatch_notification(self, node):
        """
        Integration point for 2-way alerting (ntfy.sh, notify-send, etc.)
        """
        print(f"🚨 FLATLINE: {node['hostname']} ({node['app_name']}) is down!")
        
        # Example of how notify-send integration would look:
        # os.system(f"notify-send 'Heartbeat Alert' '{node['hostname']} is down' --action='snooze=Snooze 1h' --action='ack=Acknowledge'")
        
        # Example of how ntfy.sh integration would look:
        # requests.post("https://ntfy.sh/my_private_topic",
        #     data=f"Node {node['hostname']} is offline",
        #     headers={
        #         "Actions": "view, Acknowledge, https://hb.tenthlight.com:8333/api/ack..., clear=true;"
        #     }
        # )

    def acknowledge_to_server(self, node_id):
        """Tells the upstream server the alert was dispatched."""
        ack_url = f"{self.api_url.rstrip('/')}/{node_id}/acknowledge/"
        try:
            requests.post(ack_url, auth=(self.api_user, self.api_pass), timeout=self.timeout)
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Failed to acknowledge alert for {node_id}: {e}")

    def ping_deadman(self):
        """Notifies the external monitor that HbWatcher is alive and healthy."""
        try:
            requests.get(self.deadman_url, timeout=self.timeout)
        except Exception as e:
            print(f"⚠️ Could not reach Dead Man's Switch: {e}")

    def run_forever(self):
        """The main, continuous polling loop."""
        print("🩺 HbWatcher: Starting continuous monitoring...")
        while True:
            try:
                data = self.fetch_data_with_retries()
                now = datetime.now(timezone.utc).timestamp()
                
                for node in data:
                    if node.get('alert_sent'):
                        continue
                        
                    deadline = node['received_timestamp'] + node['alert_after']
                    
                    if now > deadline:
                        self.dispatch_notification(node)
                        self.acknowledge_to_server(node.get('id'))

                # If we survived the loop without crashing/timing out, we are healthy.
                self.ping_deadman()

            except Exception as e:
                # Catch-all to prevent the watcher from dying completely on unexpected errors
                print(f"❌ HbWatcher critical loop error: {e}")
                # Notice we skip pinging the deadman here, so Healthchecks.io will alert us.

            time.sleep(self.poll_interval)


if __name__ == "__main__":
    watcher = HbWatcher()
    watcher.load_config()
    watcher.run_forever()
