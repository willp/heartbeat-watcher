#!/bin/bash
set -Eeuo pipefail

APP_NAME="hbwatcher"
INSTALL_DIR="/opt/$APP_NAME"
CONF_DIR="/etc/$APP_NAME"
SERVICE_FILE="/etc/systemd/system/$APP_NAME.service"

PURGE=false
if [[ "${1:-}" == "--purge" ]]; then
    PURGE=true
fi

echo "--- Uninstalling $APP_NAME ---"

# 1. Stop and Disable Service safely
if systemctl is-active --quiet "$APP_NAME"; then
    sudo systemctl stop "$APP_NAME"
fi

if systemctl is-enabled --quiet "$APP_NAME" 2>/dev/null; then
    sudo systemctl disable "$APP_NAME"
fi

# 2. Remove Systemd Unit File
[ -f "$SERVICE_FILE" ] && sudo rm "$SERVICE_FILE"
sudo systemctl daemon-reload
sudo systemctl reset-failed

# 3. Remove App and Venv
[ -d "$INSTALL_DIR" ] && sudo rm -rf "$INSTALL_DIR"

# 4. Handle Purge
if [ "$PURGE" = true ]; then
    echo "🔥 Purging configuration files..."
    [ -d "$CONF_DIR" ] && sudo rm -rf "$CONF_DIR"
    echo "✅ Configuration directory $CONF_DIR removed."
else
    echo "ℹ️  Configuration in $CONF_DIR preserved. Use --purge to remove it."
fi

echo "✅ Uninstallation complete."