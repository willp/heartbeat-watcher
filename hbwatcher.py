import os
import sys
import time
import json
import re
import requests
from datetime import datetime, timezone as dt_timezone
from zoneinfo import ZoneInfo  # Requires Python 3.9+

class HbWatcher:
    def __init__(self, config_path="hbwatcher_config.json"):
        self.config_path = config_path
        self.load_config()

    def load_config(self):
        with open(self.config_path, 'r') as f:
            cfg = json.load(f)
        
        self.api_url = cfg["api_url"].rstrip('/')
        self.api_user = cfg["api_user"]
        self.api_pass = cfg["api_pass"]
        self.deadman_url = cfg.get("deadman_url", "")
        self.ntfy_url = cfg.get("ntfy_url", "")
        
        self.retries = cfg.get("retries", 3)
        self.delay = cfg.get("delay", 5)
        self.timeout = cfg.get("timeout", 10)
        self.poll_interval = cfg.get("poll_interval", 60)
        
        # Pull preferred timezone from environment or fallback
        self.tz_name = os.environ.get("TZ", "America/Los_Angeles")

    def get_epoch(self):
        return int(time.time())

    def format_time(self, epoch_ts):
        """Formats timestamp dynamically (e.g., '2026-02-28 13:41 PST (47 mins ago)')"""
        if not epoch_ts: return "Unknown"
        
        # Calculate relative time
        delta = self.get_epoch() - epoch_ts
        if delta < 60: rel = f"{delta} sec"
        elif delta < 3600: rel = f"{delta // 60} mins"
        elif delta < 86400: rel = f"{delta // 3600} hours { (delta % 3600) // 60 } mins"
        else: rel = f"{delta // 86400} days { (delta % 86400) // 3600 } hours"

        # Calculate localized absolute time
        dt = datetime.fromtimestamp(epoch_ts, tz=dt_timezone.utc)
        local_dt = dt.astimezone(ZoneInfo(self.tz_name))
        abs_str = local_dt.strftime('%Y-%m-%d %H:%M %Z')
        
        return f"{abs_str} ({rel} ago)"

    def build_identifier(self, job):
        port_str = f":{job['port']}" if job.get('port') else ""
        task_str = f" [{job['task']}]" if job.get('task') else ""
        ver_str = f" (v{job['version']})" if job.get('version') else ""
        return f"{job['hostname']} | {job['app_name']}{port_str}{task_str}{ver_str}"

    def matches_filter(self, filter_str, value):
        if not filter_str: return True # Empty rule matches everything
        val_str = str(value) if value is not None else ""
        
        if filter_str.startswith('/') and filter_str.endswith('/'):
            try:
                return bool(re.search(filter_str[1:-1], val_str))
            except re.error:
                return False
        return filter_str in val_str

    def is_in_maintenance(self, job, windows):
        """Returns True if ANY active window matches ALL non-empty filters."""
        for w in windows:
            if (self.matches_filter(w.get('hostname_filter'), job.get('hostname')) and
                self.matches_filter(w.get('app_name_filter'), job.get('app_name')) and
                self.matches_filter(w.get('port_filter'), job.get('port')) and
                self.matches_filter(w.get('task_filter'), job.get('task')) and
                self.matches_filter(w.get('version_filter'), job.get('version'))):
                return True
        return False

    def fetch_data(self):
        resp = requests.get(f"{self.api_url}/watcher_data/", auth=(self.api_user, self.api_pass), timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def update_django(self, updates, failed_delivery):
        payload = {"updates": updates, "failed_delivery": failed_delivery}
        requests.post(f"{self.api_url}/bulk_transition/", json=payload, auth=(self.api_user, self.api_pass), timeout=self.timeout)

    def dispatch_notification(self, title, body):
        """Tries to send push notification with retries."""
        if not self.ntfy_url: return True
        
        for attempt in range(1, self.retries + 2):
            try:
                requests.post(self.ntfy_url, data=body.encode('utf-8'), headers={"Title": title}, timeout=self.timeout)
                return True
            except requests.exceptions.RequestException as e:
                print(f"⚠️ Push notification failed (Attempt {attempt}): {e}")
                if attempt <= self.retries:
                    time.sleep(self.delay)
        return False

    def evaluate_states(self, data):
        now = self.get_epoch()
        jobs = data['jobs']
        windows = data['maintenance_windows']
        updates = []
        messages = {"DEAD": [], "RECOVERED": [], "MAINTENANCE": []}

        for job in jobs:
            is_dead = now > (job['received_timestamp'] + job['alert_after'])
            in_maint = self.is_in_maintenance(job, windows)
            state = job['alert_state']
            ident = self.build_identifier(job)
            
            new_state = state
            msg = None
            flatlined_at = job.get('flatlined_at')

            # 1. DEAD LOGIC
            if is_dead:
                if not flatlined_at: 
                    flatlined_at = job['received_timestamp'] + job['alert_after']
                time_str = self.format_time(flatlined_at)

                if in_maint and state != 'IN_MAINTENANCE':
                    new_state = 'IN_MAINTENANCE'
                    msg = f"🔇 Suppressed: {ident} transitioned into maintenance mode due to an active rule. Dead since {time_str}."
                    messages["MAINTENANCE"].append(msg)
                
                elif not in_maint:
                    if state == 'NORMAL':
                        new_state = 'ALERT_SENT'
                        msg = f"🚨 FLATLINE: {ident} stopped responding at {time_str}."
                        messages["DEAD"].append(msg)
                    elif state == 'IN_MAINTENANCE':
                        new_state = 'ALERT_SENT'
                        msg = f"🚨 Maintenance Ended (Still Dead): {ident} never recovered. It originally died at {time_str}."
                        messages["DEAD"].append(msg)
                    elif state == 'SNOOZED' and job.get('snoozed_until', 0) < now:
                        new_state = 'ALERT_SENT'
                        msg = f"⏰ Snooze Expired: {ident} is still dead. Originally died at {time_str}."
                        messages["DEAD"].append(msg)

            # 2. ALIVE / RECOVERED LOGIC
            else:
                flatlined_at = None 
                if state in ['ALERT_SENT', 'SNOOZED']:
                    new_state = 'NORMAL'
                    msg = f"✅ Auto-Recovered: {ident} came back online. It was down since {self.format_time(job.get('flatlined_at'))}."
                    messages["RECOVERED"].append(msg)
                elif state == 'ACKNOWLEDGED':
                    new_state = 'NORMAL'
                    msg = f"✅ Resolved: You fixed {ident}! It was down since {self.format_time(job.get('flatlined_at'))}."
                    messages["RECOVERED"].append(msg)
                elif state == 'IN_MAINTENANCE':
                    new_state = 'NORMAL'
                    msg = f"✅ Silent Recovery: {ident} came back online during maintenance."
                    # Purposely NOT appending to messages["RECOVERED"] so your phone doesn't buzz.

            # If state changed, queue it for the DB update
            if new_state != state:
                updates.append({
                    "id": job['id'],
                    "previous_state": state,
                    "alert_state": new_state,
                    "flatlined_at": flatlined_at,
                    "message": msg or "State transitioned implicitly."
                })

        return updates, messages

    def run_forever(self):
        print(f"🩺 HbWatcher started. Using TZ: {self.tz_name}")
        while True:
            try:
                data = self.fetch_data()
                updates, messages = self.evaluate_states(data)

                # Batch and Send
                has_msgs = any(messages.values())
                delivery_failed = False
                
                if has_msgs:
                    title = f"Heartbeat: {len(messages['DEAD'])} Dead, {len(messages['RECOVERED'])} Recovered"
                    body = ""
                    if data.get('has_undelivered_alerts'):
                        body += "⚠️ (Previous updates *FAILED* delivery to you.)\n\n"
                    
                    for cat, msgs in messages.items():
                        if msgs: body += f"--- {cat} ---\n" + "\n".join(msgs) + "\n\n"

                    # Try to send. If False, we trigger degraded mode flag.
                    delivery_failed = not self.dispatch_notification(title, body.strip())

                # Always update Django (even if push notification failed)
                if updates or (has_msgs and not delivery_failed and data.get('has_undelivered_alerts')):
                    self.update_django(updates, delivery_failed)

                if self.deadman_url:
                    requests.get(self.deadman_url, timeout=self.timeout)

            except Exception as e:
                print(f"❌ Loop Error: {e}")
            
            time.sleep(self.poll_interval)

if __name__ == "__main__":
    w = HbWatcher()
    w.run_forever()