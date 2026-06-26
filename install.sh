#!/bin/bash
set -Eeuo pipefail

APP_NAME="hbwatcher"
INSTALL_DIR="/opt/$APP_NAME"
CONF_DIR="/etc/$APP_NAME"
SERVICE_FILE="/etc/systemd/system/$APP_NAME.service"
INTERMEDIATE_APP_NAME="nhbwatcher"
INTERMEDIATE_CONF_DIR="/etc/$INTERMEDIATE_APP_NAME"
CONFIG_NAME="hbwatcher_config.json"
INTERMEDIATE_CONFIG_NAME="nhbwatcher_config.json"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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

sudo mkdir -p "$INSTALL_DIR" "$CONF_DIR"

if [ -f "$INTERMEDIATE_CONF_DIR/$INTERMEDIATE_CONFIG_NAME" ] && [ ! -f "$CONF_DIR/$CONFIG_NAME" ]; then
    echo "Migrating config from $INTERMEDIATE_CONF_DIR/$INTERMEDIATE_CONFIG_NAME..."
    sudo cp "$INTERMEDIATE_CONF_DIR/$INTERMEDIATE_CONFIG_NAME" "$CONF_DIR/$CONFIG_NAME"
fi

if [ ! -f "$CONF_DIR/$CONFIG_NAME" ]; then
    if [ -f "$SCRIPT_DIR/example-hbwatcher_config.json" ]; then
        sudo cp "$SCRIPT_DIR/example-hbwatcher_config.json" "$CONF_DIR/$CONFIG_NAME"
    elif [ -f "$SCRIPT_DIR/$CONFIG_NAME" ]; then
        sudo cp "$SCRIPT_DIR/$CONFIG_NAME" "$CONF_DIR/$CONFIG_NAME"
    fi
fi

if [ ! -d "$INSTALL_DIR/venv" ]; then
    echo "Creating virtual environment..."
    sudo python3 -m venv "$INSTALL_DIR/venv"
fi

echo "Installing $APP_NAME package..."
sudo "$INSTALL_DIR/venv/bin/pip" install --upgrade pip --quiet
sudo "$INSTALL_DIR/venv/bin/pip" install --upgrade "$SCRIPT_DIR" --quiet

INTERMEDIATE_SERVICE="/etc/systemd/system/$INTERMEDIATE_APP_NAME.service"
if [ -f "$INTERMEDIATE_SERVICE" ]; then
    echo "Stopping intermediate $INTERMEDIATE_APP_NAME service..."
    sudo systemctl stop "$INTERMEDIATE_APP_NAME" 2>/dev/null || true
    sudo systemctl disable "$INTERMEDIATE_APP_NAME" 2>/dev/null || true
    sudo rm -f "$INTERMEDIATE_SERVICE"
fi

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
ExecStart=$INSTALL_DIR/venv/bin/hbwatcher --config $CONF_DIR/$CONFIG_NAME
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable "$APP_NAME"
sudo systemctl restart "$APP_NAME"

echo "✅ $APP_NAME is installed and active."
