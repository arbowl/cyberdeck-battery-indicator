# Cyberdeck Battery Indicator
A GUI battery indicator for Raspberry Pi and x728 UPS

## Background
I build a RasPi 4 cyberdeck and used the x728 UPS for the battery supply. It worked great, but I wanted a way to monitor the battery without having to open the provided x728bat.py script (which to their credit is hugely useful as-is and is needed to figure out how to poll the UPS).

I made this for personal use in my free time, so please be patient if there are any bugs. Feel free to reach out with any improvements, questions, or suggestions: arbowl@tutanota.com

This launches at startup and displays a battery icon on the taskbar to show the battery status. 

## How to install
1. Open a terminal
2. Enter `cd /home/pi`
3. Enter `git clone https://github.com/arbowl/cyberdeck-battery-indicator`
4. Enter `cd cyberdeck-battery-indicator`
5. Enter `chmod 755 battery_indicator.py`
6. Enter `sudo nano /etc/xdg/autostart/display.desktop`
7. Type the following:

       [Desktop Entry]
       
       Name=pi                     (or replace "pi" with your username--don't type this message in parentheses though)
       
       Exec=/usr/bin/python3 /home/pi/cyberdeck-battery-indicator/battery_indicator.py
       
8. Press ctrl+X, then press Y, then press enter
9. Done! It should now run at startup. If it doesn't work for you, cd to the directory (e.g. `cd /home/pi/cyberdeck-battery-indicator`), type `python3 battery_indicator.py`, and check for error messages. Most likely there is a path/directory or permission error.

This will download my code and the icons to a folder called "cyberdeck-battery-indicator", give users read-execute permission, then set it to run at startup.

If you rename the folder or choose a different directory, be sure to also change the variable "dir" under "if __name__ == '__main__':" in battery_indicator.py to reflect this!

## Credits
I first realized a taskbar battery indicator was feasible via this repo, and I used their icons: https://github.com/ppyne/crowPi-L_BatteryStatus

I used code from the Geekworm repo to figure out how to obtain charge info: https://github.com/geekworm-com/x728

This tutorial is helpful for creating startup routines: https://www.makeuseof.com/how-to-run-a-raspberry-pi-program-script-at-startup/
