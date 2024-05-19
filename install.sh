#!/bin/bash

USERNAME=$(whoami)
cd /home/$USERNAME || exit
git clone https://github.com/arbowl/cyberdeck-battery-indicator || exit
cd cyberdeck-battery-indicator || exit
sudo pip3 install -r requirements.txt || exit
chmod +x battery_indicator.py || exit
echo "[Desktop Entry]
Name=$USERNAME
Exec=/usr/bin/python3 /home/$USERNAME/cyberdeck-battery-indicator/battery_indicator.py" | sudo tee /etc/xdg/autostart/display.desktop > /dev/null
echo "Setup completed successfully!"
