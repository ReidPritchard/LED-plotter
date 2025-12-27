"""Improved serial communication handler for PolarPlot controller."""

import time
from collections import deque
from typing import Optional

import serial
from PyQt6.QtCore import QMutex, QMutexLocker, QThread, pyqtSignal

from models import ConnectionState


class SerialThread(QThread):
    """Background thread for serial communication to avoid blocking GUI."""

    response_received = pyqtSignal(str)
    connection_changed = pyqtSignal(ConnectionState)
    error_occurred = pyqtSignal(str)

    def __init__(self, port: str, baudrate: int = 9600):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.serial_port: Optional[serial.Serial] = None

        self.running = True

        # High-performance O(1) double-ended queue
        self.command_queue = deque()
        self.queue_lock = QMutex()

        # Flow control state
        self.current_command: Optional[str] = None
        self.waiting_for_ack = False
        self.command_sent_time: float = 0.0
        self.ack_timeout = 30.0  # seconds

    # -------------------------------------------------------------

    def run(self):
        if serial is None:
            self.error_occurred.emit("pyserial not available")
            return

        try:
            self.serial_port = serial.Serial(self.port, self.baudrate, timeout=0.1)
            self.connection_changed.emit(ConnectionState.CONNECTED)

            while self.running:
                self._read_incoming()
                self._process_ack_timeout()
                self._send_next_command()
                self._adaptive_sleep()

        except serial.SerialException as e:
            self.error_occurred.emit(f"Serial error: {str(e)}")
            self.connection_changed.emit(ConnectionState.ERROR)

        finally:
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()

            self.connection_changed.emit(ConnectionState.DISCONNECTED)

    # -------------------------------------------------------------
    # Reading & ACK handling
    # -------------------------------------------------------------

    def _read_incoming(self):
        """Handle any incoming serial data."""
        if not self.serial_port or not self.serial_port.in_waiting:
            return

        try:
            line = self.serial_port.readline().decode("utf-8").strip()
        except Exception as e:
            self.error_occurred.emit(f"Read error: {e}")
            return

        if not line:
            return

        self.response_received.emit(line)

        # State transition from WAITING_FOR_ACK → IDLE
        if line == "OK":
            self.waiting_for_ack = False
            self.current_command = None

        elif line == "BUSY":
            self.error_occurred.emit(f"Command rejected - plotter busy: {self.current_command}")
            self.waiting_for_ack = False
            self.current_command = None

        elif line == "ERR":
            self.error_occurred.emit(f"Invalid command: {self.current_command}")
            self.waiting_for_ack = False
            self.current_command = None

    # -------------------------------------------------------------

    def _process_ack_timeout(self):
        if self.waiting_for_ack and self.current_command:
            if time.time() - self.command_sent_time > self.ack_timeout:
                self.error_occurred.emit(f"Timeout waiting for response to: {self.current_command}")
                self.waiting_for_ack = False
                self.current_command = None

    # -------------------------------------------------------------
    # Command Sending
    # -------------------------------------------------------------

    def _send_next_command(self):
        """Send next command if idle."""
        if self.waiting_for_ack:
            return

        # Fast path: no commands
        if not self.command_queue:
            return

        with QMutexLocker(self.queue_lock):
            if not self.command_queue:
                return
            cmd = self.command_queue.popleft()

        try:
            self.serial_port.write(cmd.encode("utf-8") + b"\n")
        except Exception as e:
            self.error_occurred.emit(f"Write error: {e}")
            return

        self.response_received.emit(f">>> {cmd}")

        # Switch to WAITING_FOR_ACK
        self.current_command = cmd
        self.waiting_for_ack = True
        self.command_sent_time = time.time()

    # -------------------------------------------------------------
    # CPU-friendly loop pacing
    # -------------------------------------------------------------

    def _adaptive_sleep(self):
        """Use adaptive sleeping to avoid CPU spin while keeping UI responsive."""
        if self.waiting_for_ack:
            # ACK should arrive quickly; poll fast
            self.msleep(5)
        elif self.command_queue:
            # Large queues should process quickly
            self.msleep(1)
        else:
            # Idle: relax CPU
            self.msleep(20)

    # -------------------------------------------------------------
    # API methods
    # -------------------------------------------------------------

    def send_command(self, command: str):
        """Thread-safe enqueue."""
        with QMutexLocker(self.queue_lock):
            self.command_queue.append(command)

    def clear_queue(self):
        with QMutexLocker(self.queue_lock):
            self.command_queue.clear()

    def stop(self):
        self.running = False
