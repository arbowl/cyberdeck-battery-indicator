# Cyberdeck Battery Indicator
A GUI battery indicator for raspberry pi and x728 UPS

## Background
I build a RasPi 4 cyberdeck and used the x728 UPS for the battery supply. It worked great, but I wanted a way to monitor the battery without having to open the provided x728bat.py script (which to their credit is hugely useful as-is and needed to figure out how to poll the UPS).

This launches at startup and displays a battery icon on the taskbar to show the battery status. 

## How to use
1. Clone the repo (via 'git clone https://github.com/arbowl/cyberdeck-battery-indicator')
2. Drag the folder to a suitable location
3. Create a startup routine via /etc/xdg/autostart/display.desktop

## Credits
I first realized a taskbar battery indicator was feasible via this repo, and I used their icons: https://github.com/ppyne/crowPi-L_BatteryStatus

I used code from the Geekworm repo to figure out how to obtain charge info: https://github.com/geekworm-com/x728

This tutorial is helpful for creating startup routines: https://www.makeuseof.com/how-to-run-a-raspberry-pi-program-script-at-startup/
