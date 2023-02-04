import struct
from time import sleep

import RPi.GPIO as GPIO
import smbus2 as smbus
from PyQt5.QtCore import QMutex, QObject, QThread, pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QAction, QApplication, QMenu, QSystemTrayIcon

# Initializes the app; placed here to buffer init time
app = QApplication([])

class BatteryPoller(QObject):
    """The threaded worker object which polls the battery in the background

    Args:
        QObject (_type_): PyQt5 compatibility object
    """
    finished = pyqtSignal()
    update_tray = pyqtSignal(bool, float, float, float)
    
    def __init__(self):
        super().__init__()
        self._running = True
        self._mutex = QMutex()
        self.update_tray.connect(update_battery_status)
    
    def stop(self):
        """Updates the mutex if the app is closed
        """
        self._mutex.lock()
        self._running = False
        self._mutex.unlock()
        
    def is_running(self):
        """Determines if the user stopped the thread

        Returns:
            bool: Status of _is_running
        """
        try:
            self._mutex.lock()
            return self._running
        finally:
            self._mutex.unlock()

    def run(self):
        """Every second, checks the charging status, battery voltage, battery charge,
        and estimates the remaining battery life. Loops until the user exits
        """
        # A queue to primitively calculate remaining battery life (time)
        battery_queue = []
        # The length of time in seconds to get a delta capacity value
        seconds_of_capacity_polling = 300
        while self.is_running():
            # True if the battery is being used
            battery_power = GPIO.input(GPIO_PWR_PORT)
            
            # Reads the voltage
            voltage_address = bus.read_word_data(I2C_ADDR, 2)
            voltage_as_a_float = struct.unpack('<H', struct.pack('>H', voltage_address))[0]
            battery_voltage = voltage_as_a_float * 1.25 / 1000 / 16
            
            # Reads the charge
            charge_address = bus.read_word_data(I2C_ADDR, 4)
            charge_as_a_float = struct.unpack('<H', struct.pack('>H', charge_address))[0]
            battery_charge = charge_as_a_float / 256
            if battery_charge > 100:
                battery_charge = 100
            
            # Calculates battery drain duration
            if len(battery_queue) <= seconds_of_capacity_polling:
                battery_queue.append(battery_charge)
            else:
                battery_queue.pop(0)
                battery_queue.append(battery_charge)
            battery_time = (battery_queue[0] - battery_queue[-1]) / len(battery_queue) * 60
            # Estimation during the first ~min when there's no change to avoid divide-by-zero errors
            if battery_time == 0:
                battery_time = 0.2
            battery_time = battery_charge / battery_time
            
            # If charging, reset the queue
            if not battery_power:
                battery_queue = []
            
            # Updates the GUI
            self.update_tray.emit(battery_power, battery_voltage, battery_charge, battery_time)
            sleep(1)
            
        self.finished.emit()


def update_battery_status(on_battery_power, voltage, charge, time):
    """Updates the GUI according to the charging status and battery capacity

    Args:
        on_battery_power (bool): If the battery is charging it will show a charge symbol
        voltage (float): The actual voltage of the battery
        percent (float): The converted estimated percent of the battery capacity
        time (float): The number of minutes estimated to be left
    """
    display_voltage = round(voltage, 2)
    display_charge = round(charge, 1)
    # If the battery isn't charging...
    if on_battery_power:
        # This converts a % to a number from 0-7 which matches a battery level icon
        icon_to_display = round(display_charge / (100 / 7))
        # And the rest formats the time remaining value
        display_time = abs(int(round(time)))
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
        icon_to_display = 'Charging'
        display_time = 'Charging'
        
    # Dangerously low voltage
    if display_voltage < 3.00:
        icon_to_display = 'Warning'
    
    # Update visual elements
    tray_icon.setIcon(battery_state_icons[icon_to_display])
    tray_icon.setToolTip(str(display_charge) + '%, ' + str(display_voltage) + 'V, ' + display_time)
    

if __name__ == '__main__':
    dir = '/home/pi/cyberdeck-battery-indicator/'
    battery_state_icons = {
            0 : QIcon(dir + 'battery_0.png'),
            1 : QIcon(dir + 'battery_1.png'),
            2 : QIcon(dir + 'battery_2.png'),
            3 : QIcon(dir + 'battery_3.png'),
            4 : QIcon(dir + 'battery_4.png'),
            5 : QIcon(dir + 'battery_5.png'),
            6 : QIcon(dir + 'battery_6.png'),
            7 : QIcon(dir + 'battery_7.png'),
            'Charging' : QIcon(dir + 'battery_charging.png'),
            'Warning' :QIcon(dir + 'battery_alert.png')
    }
    
    # x728 UPS defaults
    I2C_ADDR = 0x36
    GPIO_ASD_PORT = 26
    GPIO_BATT_PORT = 13
    GPIO_PWR_PORT = 6
    bus = smbus.SMBus(1)
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(GPIO_BATT_PORT, GPIO.OUT)
    GPIO.setup(GPIO_PWR_PORT, GPIO.IN)
    
    # Create the application and tray icon
    app.setQuitOnLastWindowClosed(False)
    tray_icon = QSystemTrayIcon()
    tray_icon.setIcon(battery_state_icons[9])
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
