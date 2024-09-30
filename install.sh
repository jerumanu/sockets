#!/bin/bash

pip install -r requirements.txt

# Set up server as a systemd service
cat << EOF | sudo tee "$SERVICE_FILE"
[Unit]
Description=Search Server
After=network.target

[Service]
WorkingDirectory=/algo-tests/
ExecStart=/usr/bin/python3 /algo-tests/server/server.py
# Restart=always
User=user
Group=user

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd, enable and start the service
sudo systemctl daemon-reload
sudo systemctl enable search_server
sudo systemctl start search_server

# Check the service status
# sudo systemctl status search_server
