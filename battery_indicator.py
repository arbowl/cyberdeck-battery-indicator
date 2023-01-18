import struct
import time
from math import ceil
from time import sleep

import RPi.GPIO as GPIO
import smbus
from PyQt5.QtCore import QMutex, QObject, QThread, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QAction, QApplication, QMenu, QSystemTrayIcon

app = QApplication([])

class BatteryPoller(QObject):
    """The threaded worker object which polls the battery in the background

    Args:
        QObject (_type_): PyQt5 compatibility object
    """
    finished = pyqtSignal()
    update_tray = pyqtSignal(bool, float, float)
    
    def __init__(self):
        super().__init__()
        self._is_running = True
        self._mutex = QMutex()
        self.update_tray.connect(update_battery_status)
    
    def stop(self):
        """Updates the mutex if the app is closed
        """
        self._mutex.lock()
        self.is_running = False
        self._mutex.unlock()
        
    def is_running(self):
        """Determines if the user stopped the thread

        Returns:
            bool: Status of _is_running
        """
        try:
            self._mutex.lock()
            return self._is_running
        finally:
            self._mutex.unlock()

    def run(self):
        """Every second, polls the voltage, charge, and charging status
        """
        battery_queue = []
        while self.is_running():
            # True if the battery is being used
            battery_power = GPIO.input(GPIO_PWR_PORT)
            
            # Reads the voltage
            voltage = bus.read_word_data(I2C_ADDR, 2)
            voltage_in_bytes = struct.unpack('<H', struct.pack('>H', voltage))[0]
            battery_voltage = voltage_in_bytes * 1.25 / 1000 / 16
            
            # Reads the charge
            charge = bus.read_word_data(I2C_ADDR, 4)
            charge_in_bytes = struct.unpack('<H', struct.pack('>H', charge))[0]
            battery_capacity = charge_in_bytes / 256
            if battery_capacity > 100:
                battery_capacity = 100
            
            # Compares charge values across several minutes to primitively calculate battery drain
            if len(battery_queue) <= 300:
                battery_queue.append(battery_capacity)
            else:
                battery_queue.pop(0)
                battery_queue.append(battery_capacity)
            time_remaining = (battery_queue[0] - battery_queue[-1]) / len(battery_queue) * 60
            if time_remaining == 0:
                time_remaining = 0.2
            time_remaining = battery_capacity / time_remaining
            
            # If charging, reset the queue
            if not battery_power:
                battery_queue = []
            
            # Updates the GUI
            self.update_tray.emit(battery_power, battery_voltage, battery_capacity, time_remaining)
            sleep(1)
            
        self.finished.emit()


def update_battery_status(on_battery_power, voltage, percent, time):
    """Updates the GUI according to the charging status and battery capacity

    Args:
        on_battery_power (bool): If the battery is charging it will show a charge symbol
        voltage (float): The actual voltage of the battery
        percent (float): The converted estimated percent of the battery capacity
        time (float): The number of minutes estimated to be left
    """
    display_voltage = round(voltage, 2)
    display_charge = round(percent, 1)
    # If the battery isn't charging...
    if on_battery_power:
        icon_to_display = ceil(display_charge / (100 / 7))
        display_time = int(round(time, 0))
        if display_time < 60:
            display_time = str(display_time) + ' min'
        else:
            hours_left = str(int(round(display_time / 60, 0)))
            minutes_left = str(int(round(display_time % 60, 0)))
            if len(minutes_left) == 1:
                minutes_left = '0' + minutes_left
            display_time = hours_left + ':' + minutes_left + ' hrs'
    # If the battery is charging, show a charge icon
    else:
        icon_to_display = 8
        display_time = 'Charging'
    tray_icon.setIcon(battery_icons[icon_to_display])
    tray_icon.setToolTip(str(display_charge) + '%, ' + str(display_voltage) + 'V, ' + display_time)
    
    # Dangerously low voltage
    if display_voltage < 3.00:
        icon_to_display = 9


if __name__ == '__main__':
    battery_icons = [
            QIcon('battery_0.png'),
            QIcon('battery_1.png'),
            QIcon('battery_2.png'),
            QIcon('battery_3.png'),
            QIcon('battery_4.png'),
            QIcon('battery_5.png'),
            QIcon('battery_6.png'),
            QIcon('battery_7.png'),
            QIcon('battery_charging.png'),
            QIcon('battery_alert.png')
    ]
    
    # x728 UPS defaults
    I2C_ADDR = 0x36
    GPIO_ASD_PORT = 26
    GPIO_BATT_PORT = 13
    GPIO_PWR_PORT = 6
    bus = smbus.SMBus(1)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(GPIO_BATT_PORT, GPIO.OUT)
    GPIO.setup(GPIO_PWR_PORT, GPIO.IN)
    GPIO.setwarnings(False)
    
    # Create the application and tray icon
    app.setQuitOnLastWindowClosed(False)
    tray_icon = QSystemTrayIcon()
    tray_icon.setIcon(battery_icons[9])
    tray_icon.setVisible(True)

    # Create the worker thread
    polling_thread = QThread()
    battery_worker = BatteryPoller()
    battery_worker.moveToThread(polling_thread)
    polling_thread.started.connect(battery_worker.run)
    battery_worker.finished.connect(polling_thread.quit)
    battery_worker.finished.connect(polling_thread.wait)
    battery_worker.finished.connect(battery_worker.deleteLater)
    polling_thread.start()

    # Create the clickable menu
    menu = QMenu()
    quit = QAction('Exit')
    quit.triggered.connect(battery_worker.stop)
    quit.triggered.connect(app.quit)
    menu.addAction(quit)
    tray_icon.setContextMenu(menu)

    # Start the execution loop
    app.exec()