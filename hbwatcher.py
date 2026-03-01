#!/usr/bin/python3
import os
import time
import json
import re
import requests
import platform
from datetime import datetime, timezone as dt_timezone
from zoneinfo import ZoneInfo

VERSION = "1.1.0"

class HbWatcher:
    def __init__(self, config_path="hbwatcher_config.json"):
        self.config_path = config_path
        self.load_config()
        self.user_agent = f"HbWatcher/{VERSION} (Python {platform.python_version()})"
        
        # Initialize the nag timer so it is primed to nag immediately 
        # on the first loop if things are already broken upon restart.
        self.last_alert_time = self.get_epoch() - self.nag_interval

    def load_config(self):
        with open(self.config_path, 'r') as f:
            cfg = json.load(f)
        
        self.api_url = cfg["api_url"].rstrip('/')
        self.api_user = cfg["api_user"]
        self.api_pass = cfg["api_pass"]
        self.deadman_url = cfg.get("deadman_url", "")
        self.ntfy_url = cfg.get("ntfy_url", "")
        self.ntfy_token = cfg.get("ntfy_token", "")
        
        self.retries = cfg.get("retries", 3)
        self.delay = cfg.get("delay", 5)
        self.timeout = cfg.get("timeout", 10)
        self.poll_interval = cfg.get("poll_interval", 60)
        
        # NEW: The nag interval in seconds (default 10 mins). Set to 0 to disable.
        self.nag_interval = cfg.get("nag_interval", 600)
        
        self.tz_name = os.environ.get("TZ", "America/Los_Angeles")

    def get_epoch(self):
        return int(time.time())

    def format_time(self, epoch_ts):
        if not epoch_ts: return "Unknown"
        delta = self.get_epoch() - epoch_ts
        if delta < 60: rel = f"{delta} sec"
        elif delta < 3600: rel = f"{delta // 60} mins"
        else: rel = f"{delta // 3600} hours"

        dt = datetime.fromtimestamp(epoch_ts, tz=dt_timezone.utc)
        local_dt = dt.astimezone(ZoneInfo(self.tz_name))
        return f"{local_dt.strftime('%Y-%m-%d %H:%M %Z')} ({rel} ago)"

    def build_identifier(self, job):
        port_str = f":{job['port']}" if job.get('port') else ""
        task_str = f" [{job['task']}]" if job.get('task') else ""
        return f"{job['hostname']} | {job['app_name']}{port_str}{task_str}"

    def matches_filter(self, filter_str, value):
        if not filter_str: return True
        val_str = str(value) if value is not None else ""
        if filter_str.startswith('/') and filter_str.endswith('/'):
            try: return bool(re.search(filter_str[1:-1], val_str))
            except: return False
        return filter_str in val_str

    def is_in_maintenance(self, job, windows):
        for w in windows:
            if (self.matches_filter(w.get('hostname_filter'), job.get('hostname')) and
                self.matches_filter(w.get('app_name_filter'), job.get('app_name')) and
                self.matches_filter(w.get('port_filter'), job.get('port')) and
                self.matches_filter(w.get('task_filter'), job.get('task')) and
                self.matches_filter(w.get('version_filter'), job.get('version'))):
                return True
        return False

    def fetch_data(self):
        headers = {"User-Agent": self.user_agent}
        resp = requests.get(f"{self.api_url}/watcher_data/", auth=(self.api_user, self.api_pass), headers=headers, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def update_django(self, updates, failed_delivery):
        headers = {"User-Agent": self.user_agent}
        payload = {"updates": updates, "failed_delivery": failed_delivery}
        requests.post(f"{self.api_url}/bulk_transition/", json=payload, auth=(self.api_user, self.api_pass), headers=headers, timeout=self.timeout)

# NEW: Build the Action header string containing multiple tokens
    def build_actions_header(self, tokens_list):
        if not tokens_list: return ""
        
        # Note: Ensure self.api_url in your config is the PUBLIC url 
        # so your phone can reach it! (e.g. https://yourdomain:8333/api)
        ack_url = f"{self.api_url}/webhook/bulk_action/?action=ack"
        snooze_url = f"{self.api_url}/webhook/bulk_action/?action=snooze"
        
        for t in tokens_list:
            if t.get('ack') and t.get('snooze'):
                ack_url += f"&t={t['ack']}"
                snooze_url += f"&t={t['snooze']}"
        
        # 'clear=true' dismisses the notification upon successful tap
        return f"http, Acknowledge All, {ack_url}, method=POST, clear=true; http, Snooze 1 hr, {snooze_url}, method=POST, clear=true"

    def dispatch_notification(self, title, body, priority="default", tags="", actions=""):
        if not self.ntfy_url: return True
        headers = {"Title": title, "Priority": priority, "User-Agent": self.user_agent}
        if tags: headers["Tags"] = tags
        if actions: headers["Actions"] = actions # <--- Inject the buttons
        if self.ntfy_token: headers["Authorization"] = f"Bearer {self.ntfy_token}"
        
        for attempt in range(1, self.retries + 2):
            try:
                requests.post(self.ntfy_url, data=body.encode('utf-8'), headers=headers, timeout=self.timeout)
                return True
            except:
                if attempt <= self.retries: time.sleep(self.delay)
        return False

    def evaluate_states(self, data):
        now = self.get_epoch()
        jobs = data['jobs']
        windows = data['maintenance_windows']
        updates = []
        messages = {"DEAD": [], "RECOVERED": [], "MAINTENANCE": []}
        
        currently_dead = [] 
        new_dead_tokens = [] # <--- Track tokens for immediately triggered alerts

        for job in jobs:
            is_dead = now > (job['received_timestamp'] + job['alert_after'])
            in_maint = self.is_in_maintenance(job, windows)
            state = job['alert_state']
            ident = self.build_identifier(job)
            new_state = state
            msg = None
            flatlined_at = job.get('flatlined_at')

            if is_dead:
                if not flatlined_at: flatlined_at = job['received_timestamp'] + job['alert_after']
                time_str = self.format_time(flatlined_at)
                if in_maint and state != 'IN_MAINTENANCE':
                    new_state = 'IN_MAINTENANCE'
                    msg = f"🔇 Suppressed: {ident} is in maintenance. Dead since {time_str}."
                    messages["MAINTENANCE"].append(msg)
                elif not in_maint:
                    if state == 'NORMAL':
                        new_state = 'ALERT_SENT'
                        msg = f"🚨 FLATLINE: {ident} died at {time_str}."
                        messages["DEAD"].append(msg)
                    elif state == 'IN_MAINTENANCE':
                        new_state = 'ALERT_SENT'
                        msg = f"🚨 Maintenance Ended: {ident} is still dead. Died at {time_str}."
                        messages["DEAD"].append(msg)
                    elif state == 'SNOOZED' and job.get('snoozed_until', 0) < now:
                        new_state = 'ALERT_SENT'
                        msg = f"⏰ Snooze Expired: {ident} is still dead. Died at {time_str}."
                        messages["DEAD"].append(msg)
            else:
                flatlined_at = None 
                if state in ['ALERT_SENT', 'SNOOZED', 'ACKNOWLEDGED']:
                    new_state = 'NORMAL'
                    msg = f"✅ Recovered: {ident} is back online."
                    messages["RECOVERED"].append(msg)

            # Record if it's currently unhandled
            if new_state == 'ALERT_SENT':
                currently_dead.append({
                    "ident": ident, 
                    "ack": job.get('ack_token'), 
                    "snooze": job.get('snooze_token')
                })
                # If this is a newly triggered alert, grab tokens for the standard push
                if state != 'ALERT_SENT':
                    new_dead_tokens.append({
                        "ack": job.get('ack_token'), 
                        "snooze": job.get('snooze_token')
                    })

            if new_state != state:
                updates.append({"id": job['id'], "previous_state": state, "alert_state": new_state, "flatlined_at": flatlined_at, "message": msg or "Auto-transition."})
                
        return updates, messages, currently_dead, new_dead_tokens

    def run_forever(self):
        print(f"🩺 HbWatcher v{VERSION} started. TZ: {self.tz_name}")
        last_deadman_ping_ts = 0
        while True:
            try:
                data = self.fetch_data()
                # Unpack the new return value
                updates, messages, currently_dead, new_dead_tokens = self.evaluate_states(data)
                
                alert_dispatched = False

                # 1. Handle Standard State Transitions
                if any(messages.values()):
                    prio = "urgent" if messages["DEAD"] else "default"
                    tags = "rotating_light,skull" if messages["DEAD"] else "white_check_mark"
                    body = "\n\n".join([f"--- {k} ---\n" + "\n".join(v) for k, v in messages.items() if v])
                    
                    # Generate action buttons if there are new dead jobs
                    actions = ""
                    if messages["DEAD"] and new_dead_tokens:
                        actions = self.build_actions_header(new_dead_tokens)
                        
                    delivery_failed = not self.dispatch_notification("Heartbeat Update", body, prio, tags, actions)
                    self.update_django(updates, delivery_failed)
                    alert_dispatched = True

                elif updates:
                    self.update_django(updates, False)

                # 2. Handle the Nag Timer
                now = self.get_epoch()
                if alert_dispatched:
                    self.last_alert_time = now
                elif self.nag_interval > 0 and currently_dead:
                    if (now - self.last_alert_time) >= self.nag_interval:
                        nag_title = f"Reminder: {len(currently_dead)} Job(s) Offline"
                        nag_body = "The following jobs are still DEAD and unacknowledged:\n\n"
                        nag_body += "\n".join([f"- {job['ident']}" for job in currently_dead])
                        
                        # Apply buttons to ALL dead jobs in the nag summary
                        actions = self.build_actions_header(currently_dead)
                        
                        self.dispatch_notification(nag_title, nag_body, priority="urgent", tags="rotating_light,alarm_clock", actions=actions)
                        self.last_alert_time = now

                # 3. Deadman Switch
                since_last_deadman_ping = time.time() - last_deadman_ping_ts
                if self.deadman_url and since_last_deadman_ping > 30:
                    try:
                        requests.get(self.deadman_url, timeout=self.timeout, headers={"User-Agent": self.user_agent},)
                    finally:
                        last_deadman_ping_ts = time.time()
                
            except Exception as e: print(f"❌ Error: {e}")
            
            time.sleep(self.poll_interval)

if __name__ == "__main__":
    w = HbWatcher()
    w.run_forever()
