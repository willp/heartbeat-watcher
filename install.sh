#!/bin/bash
set -Eeuo pipefail

APP_NAME="hbwatcher"
INSTALL_DIR="/opt/$APP_NAME"
CONF_DIR="/etc/$APP_NAME"
SERVICE_FILE="/etc/systemd/system/$APP_NAME.service"

# Detect distro and provide instructions for missing venv
check_venv_or_die() {
    if ! python3 -m venv --help > /dev/null 2>&1; then
        echo "❌ Error: Python 'venv' module is not installed."
        if [ -f /etc/os-release ]; then
            . /etc/os-release
            case "$ID" in
                ubuntu|debian|kali|raspbian)
                    echo "👉 Run: sudo apt update && sudo apt install python3-venv" ;;
                fedora|centos|rhel|almalinux|rocky)
                    echo "👉 Run: sudo dnf install python3" ;; 
                arch|manjaro)
                    echo "👉 Run: sudo pacman -S python" ;;
                *)
                    echo "👉 Please install the python3 venv package for your distribution." ;;
            esac
        fi
        exit 1
    fi
}

echo "--- Installing $APP_NAME ---"
check_venv_or_die

# 1. Create Directories
sudo mkdir -p "$INSTALL_DIR" "$CONF_DIR"

# 2. Sync Files (Update script, but preserve existing config)
echo "Syncing application files..."
[ -f hbwatcher.py ] && sudo cp hbwatcher.py "$INSTALL_DIR/"
[ -f hbwatcher_config.json ] && [ ! -f "$CONF_DIR/hbwatcher_config.json" ] && sudo cp hbwatcher_config.json "$CONF_DIR/"

# 3. Setup/Update Virtual Environment
if [ ! -d "$INSTALL_DIR/venv" ]; then
    echo "Creating virtual environment..."
    sudo python3 -m venv "$INSTALL_DIR/venv"
fi

# 4. Install dependencies (Silent upgrade)
echo "Ensuring dependencies are met..."
sudo "$INSTALL_DIR/venv/bin/pip" install --upgrade pip --quiet
sudo "$INSTALL_DIR/venv/bin/pip" install requests --quiet

# 5. Create/Refresh Systemd Service
echo "Registering systemd service..."
cat <<EOF | sudo tee "$SERVICE_FILE" > /dev/null
[Unit]
Description=Heartbeat Watcher Daemon
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$INSTALL_DIR
Environment=PYTHONUNBUFFERED=1
Environment=TZ=$(cat /etc/timezone 2>/dev/null || echo "UTC")
ExecStart=$INSTALL_DIR/venv/bin/python3 $INSTALL_DIR/hbwatcher.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 6. Reload and Kickstart
sudo systemctl daemon-reload
sudo systemctl enable "$APP_NAME"
sudo systemctl restart "$APP_NAME"

echo "✅ $APP_NAME is installed and active."