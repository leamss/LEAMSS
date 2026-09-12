#!/bin/bash
# ==============================================================================
# LEAMSS Auto-Deploy Daemon Installer for EC2
# Sets up a 30-second automated sync daemon using systemd
# ==============================================================================

set -e

chmod +x /home/ubuntu/LEAMSS/scripts/auto_deploy.sh

# Create systemd service
sudo tee /etc/systemd/system/leamss-autodeploy.service > /dev/null << 'EOF'
[Unit]
Description=LEAMSS Continuous Auto-Deploy Daemon
After=network.target docker.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/LEAMSS
ExecStart=/bin/bash -c "while true; do /home/ubuntu/LEAMSS/scripts/auto_deploy.sh >> /var/log/leamss-autodeploy.log 2>&1; sleep 30; done"
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Reload and start systemd daemon
sudo systemctl daemon-reload
sudo systemctl enable leamss-autodeploy.service
sudo systemctl restart leamss-autodeploy.service

echo "Triggering initial full build and deploy..."
/home/ubuntu/LEAMSS/scripts/auto_deploy.sh --force

echo "==================================================================="
echo "✅ LEAMSS Continuous Auto-Deploy Daemon successfully installed!"
echo "Status: Active & monitoring GitHub main branch every 30 seconds."
echo "Logs: tail -f /var/log/leamss-autodeploy.log"
echo "==================================================================="
