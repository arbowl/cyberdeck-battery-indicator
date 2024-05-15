"""Battery Indicator

I made this for the x728 UPS to show the battery level in the system tray, because
I found that it was difficult to use it unplugged without knowing how much battery
was left. The scripts that come with the device are useful for seeing the battery
in the terminal, but this makes it more accessible.

https://github.com/arbowl/cyberdeck-battery-indicator/
"""

from collections import deque
from enum import Enum, IntEnum
from struct import pack, unpack
from time import sleep

from RPi.GPIO import input as gpio_input, setwarnings, setup, setmode, BCM, OUT, IN
from smbus2 import SMBus
from PyQt5.QtCore import QMutex, QObject, QThread, pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QAction, QApplication, QMenu, QSystemTrayIcon

from directory import ICON_DIR


class GpioPins(IntEnum):
    """Pin constants for the RasPi and x728"""

    I2C_ADDR = 0x36
    GPIO_ASD_PORT = 26
    GPIO_BATT_PORT = 13
    GPIO_PWR_PORT = 6


class SpecialIcons(str, Enum):
    """Class to hold non-numerical battery statuses"""

    WARNING = "Warning"
    CHARGING = "Charging"


class BatteryPoller(QObject):
    """The threaded worker object which polls the battery in the background"""

    finished = pyqtSignal()
    update_tray = pyqtSignal(QSystemTrayIcon, bool, float, float, float)
    battery_state_icons = {
        0: QIcon(ICON_DIR + "battery_0.png"),
        1: QIcon(ICON_DIR + "battery_1.png"),
        2: QIcon(ICON_DIR + "battery_2.png"),
        3: QIcon(ICON_DIR + "battery_3.png"),
        4: QIcon(ICON_DIR + "battery_4.png"),
        5: QIcon(ICON_DIR + "battery_5.png"),
        6: QIcon(ICON_DIR + "battery_6.png"),
        7: QIcon(ICON_DIR + "battery_7.png"),
        SpecialIcons.WARNING: QIcon(ICON_DIR + "battery_alert.png"),
        SpecialIcons.CHARGING: QIcon(ICON_DIR + "battery_charging.png"),
    }

    def __init__(self) -> None:
        super().__init__()
        self._running = True
        self._mutex = QMutex()
        self.update_tray.connect(update_battery_status)
        self.bus = SMBus(1)
        self.tray_icon = QSystemTrayIcon()
        self.tray_icon.setIcon(BatteryPoller.battery_state_icons[SpecialIcons.WARNING])
        self.tray_icon.setVisible(True)

    def stop(self) -> None:
        """Updates the mutex if the app is closed"""
        self._mutex.lock()
        self._running = False
        self._mutex.unlock()

    def is_running(self) -> bool:
        """Determines if the user stopped the thread

        Returns:
            bool: Status of _is_running
        """
        try:
            self._mutex.lock()
            return self._running
        finally:
            self._mutex.unlock()

    def run(self) -> None:
        """Every second, checks the charging status, battery voltage, battery charge,
        and estimates the remaining battery life. Loops until the user exits. The
        length of the battery queue can be set to anything. The battery estimation is
        meant to be a simple approximation and is linear; this does not implement
        CC, CV, curves, or anything more advanced than a simple y=mx+b calculation!
        """
        battery_queue: deque = deque(maxlen=300)
        while self.is_running():
            battery_power = gpio_input(GpioPins.GPIO_PWR_PORT)
            voltage_address = self.bus.read_word_data(GpioPins.I2C_ADDR, 2)
            voltage_as_a_float = unpack("<H", pack(">H", voltage_address))[0]
            battery_voltage = voltage_as_a_float * 1.25 / 1000 / 16
            charge_address = self.bus.read_word_data(GpioPins.I2C_ADDR, 4)
            charge_as_a_float = unpack("<H", pack(">H", charge_address))[0]
            battery_charge = charge_as_a_float / 256
            battery_charge = min(battery_charge, 100)
            battery_queue.append(battery_charge)
            battery_time = (
                (battery_queue[0] - battery_queue[-1]) / len(battery_queue) * 60
            )
            # Estimation during the first ~min to avoid divide-by-zero errors
            if battery_time == 0:
                battery_time = 0.2
            battery_time = battery_charge / battery_time
            if not battery_power:
                battery_queue.clear()
            self.update_tray.emit(
                self.tray_icon,
                battery_power,
                battery_voltage,
                battery_charge,
                battery_time,
            )
            sleep(1)
        self.finished.emit()


def update_battery_status(
    icon: QSystemTrayIcon, unplugged: bool, voltage: float, charge: float, time: float
) -> None:
    """Updates the GUI according to the charging status and battery capacity

    Args:
        icon (QSystemTrayicon): The tray icon to update
        unplugged (bool): If the battery is charging it will show a charge symbol
        voltage (float): The actual voltage of the battery
        percent (float): The converted estimated percent of the battery capacity
        time (float): The number of minutes estimated to be left
    """
    display_voltage = round(voltage, 2)
    display_charge = round(charge, 1)
    if unplugged:
        # This converts a % to a number from 0-7 which matches a battery level icon
        icon_to_display: str | int = round(display_charge / (100 / 7))
        time_remaining = abs(int(round(time)))
        if time_remaining < 60:
            display_time = str(time_remaining) + " min"
        else:
            hours_left = str(int(round(time_remaining / 60, 0)))
            minutes_left = str(int(round(time_remaining % 60, 0)))
            if len(minutes_left) == 1:
                minutes_left = "0" + minutes_left
            display_time = hours_left + ":" + minutes_left + " hrs"
    else:
        icon_to_display = SpecialIcons.CHARGING
        display_time = SpecialIcons.CHARGING
    if display_voltage < 3.00:
        icon_to_display = SpecialIcons.WARNING
    icon.setIcon(BatteryPoller.battery_state_icons[icon_to_display])
    icon.setToolTip(
        str(display_charge) + "%, " + str(display_voltage) + "V, " + display_time
    )


def configure_gpio() -> None:
    """Configures the GPIO in/out pins"""
    setwarnings(False)
    setmode(BCM)
    setup(GpioPins.GPIO_BATT_PORT, OUT)
    setup(GpioPins.GPIO_PWR_PORT, IN)


def spawn_icon_thread(application: QApplication) -> None:
    """Spawns the thread which updates the system tray icon"""
    polling_thread = QThread()
    battery_worker = BatteryPoller()
    battery_worker.moveToThread(polling_thread)
    polling_thread.started.connect(battery_worker.run)
    battery_worker.finished.connect(polling_thread.quit)
    battery_worker.finished.connect(battery_worker.deleteLater)
    polling_thread.start()
    menu = QMenu()
    quit_app = QAction("Exit")
    quit_app.triggered.connect(battery_worker.stop)
    quit_app.triggered.connect(application.quit)
    menu.addAction(quit_app)
    battery_worker.tray_icon.setContextMenu(menu)


def main() -> None:
    """Launches the app and spawns the"""
    app = QApplication([])
    sleep(5)
    configure_gpio()
    spawn_icon_thread(app)
    app.setQuitOnLastWindowClosed(False)
    app.exec()


if __name__ == "__main__":
    main()
