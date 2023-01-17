import smbus
import time
import struct
from math import ceil
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QAction
from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot, QMutex
import RPi.GPIO as GPIO

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
        while self._is_running:
            charging_status = GPIO.input(GPIO_PWR_PORT)
            
            voltage = bus.read_word_data(I2C_ADDR, 2)
            voltage_in_bytes = struct.unpack('<H', struct.pack('>H', voltage))[0]
            battery_voltage = voltage_in_bytes * 1.25 / 1000 / 16
            
            charge = bus.read_word_data(I2C_ADDR, 4)
            charge_in_bytes = struct.unpack('<H', struct.pack('>H', charge))[0]
            battery_capacity = charge_in_bytes / 256
            if battery_capacity > 100:
                battery_capacity = 100

            self.update_tray.emit(charging_status, battery_voltage, battery_capacity)
            time.sleep(1)
            
        self.finished.emit()


def update_battery_status(on_battery_power, voltage, percent):
    """Updates the GUI according to the charging status and battery capacity

    Args:
        battery_charging (bool): If the battery is charging it will show a charge symbol
        voltage (float): The actual voltage of the battery
        percent (float): The converted estimated percent of the battery capacity
    """
    volts = round(voltage, 2)
    charge = round(percent, 1)
    # If the battery isn't charging...
    if on_battery_power:
        # ...show the % if it's > 20,...
        if charge >= 20:
            icon_to_display = ceil(charge / (100 / 7))
        # ...or a danger symbol to prompt the user to charge
        else:
            icon_to_display = 9
    # If the battery is charging, show a charge icon
    else:
        icon_to_display = 8
    tray_icon.setIcon(battery_icons[icon_to_display])
    tray_icon.setToolTip(str(charge) + '% ' + str(volts) + 'V')


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