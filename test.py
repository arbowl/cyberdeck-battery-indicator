import smbus
import time
import struct
from math import ceil
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QAction
from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot, QMutex
import RPi.GPIO as GPIO


class Worker(QObject):
    finished = pyqtSignal()
    update_tray = pyqtSignal(bool, float, float)
    
    def __init__(self):
        super().__init__()
        self._is_running = False
        self._mutex = QMutex()
        self.update_tray.connect(update_battery_status)
    
    def stop(self) -> None:
        self._mutex.lock()
        self.is_running = False
        self._mutex.unlock()
        
    def is_running(self) -> bool:
        try:
            self._mutex.lock()
            return self._is_running
        finally:
            self._mutex.unlock()

    def run(self) -> None:
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


def update_battery_status(battery_charging: bool, voltage: float, percent: float) -> None:
    volts = round(voltage, 2)
    charge = round(percent, 1)
    if not battery_charging:
        icon_to_display = ceil(voltage / (100 / 7))
    else:
        icon_to_display = icons[8]
    tray_icon.setIcon(icons[icon_to_display])
    hover_info = str(charge) + '% ' + str(volts) + 'V'
    tray_icon.setToolTip(hover_info)


if __name__ == '__main__':
    icons = [
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
    
    I2C_ADDR = 0x36
    GPIO_BATT_PORT = 13
    GPIO_PWR_PORT = 6
    bus = smbus.SMBus(1)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(GPIO_BATT_PORT, GPIO.OUT)
    GPIO.setup(GPIO_BATT_PORT, GPIO.IN)
    GPIO.setwarnings(False)
    
    app = QApplication([])
    app.setQuitOnLastWindowClosed(False)
    
    tray_icon = QSystemTrayIcon()
    tray_icon.setIcon(icons[10])
    tray_icon.setVisible(True)

    thread = QThread()
    worker = Worker()
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.finished.connect(thread.quit)
    worker.finished.connect(worker.deleteLater)
    worker.finished.connect(app.quit)
    thread.finished.connect(thread.deleteLater)
    worker.update_tray.connect(update_battery_status)
    thread.start()

    # Create the menu
    menu = QMenu()
    quit = QAction('Exit')
    quit.triggered.connect(worker.stop)
    menu.addAction(quit)
    tray_icon.setContextMenu(menu)

    app.exec_()