"""Serial communication handler for PolarPlot controller."""

from typing import Optional

from PyQt6.QtCore import QThread, pyqtSignal

from models import ConnectionState

# Try to import serial, gracefully handle if not installed
try:
    import serial

    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False
    print("Warning: pyserial not installed. Install with: pixi add pyserial")


class SerialThread(QThread):
    """Background thread for serial communication to avoid blocking GUI."""

    # AIDEV-NOTE: Signals for thread-safe communication with GUI
    response_received = pyqtSignal(str)
    connection_changed = pyqtSignal(ConnectionState)
    error_occurred = pyqtSignal(str)

    def __init__(self, port: str, baudrate: int = 9600):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.serial_port: Optional[serial.Serial] = None
        self.running = True
        self.command_queue = []

    def run(self):
        """Main thread loop - handle serial I/O."""
        if not SERIAL_AVAILABLE:
            self.error_occurred.emit("pyserial not installed")
            return

        try:
            self.serial_port = serial.Serial(
                self.port, self.baudrate, timeout=0.1
            )
            self.connection_changed.emit(ConnectionState.CONNECTED)

            while self.running:
                # Read any incoming data
                if self.serial_port.in_waiting:
                    try:
                        line = (
                            self.serial_port.readline().decode("utf-8").strip()
                        )
                        if line:
                            self.response_received.emit(line)
                    except Exception as e:
                        self.error_occurred.emit(f"Read error: {str(e)}")

                # Send queued commands
                if self.command_queue:
                    cmd = self.command_queue.pop(0)
                    try:
                        self.serial_port.write(f"{cmd}\n".encode("utf-8"))
                        self.response_received.emit(f">>> {cmd}")
                    except Exception as e:
                        self.error_occurred.emit(f"Write error: {str(e)}")

                self.msleep(10)  # Small delay to prevent CPU spinning

        except serial.SerialException as e:
            self.error_occurred.emit(f"Serial error: {str(e)}")
            self.connection_changed.emit(ConnectionState.ERROR)
        finally:
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()
            self.connection_changed.emit(ConnectionState.DISCONNECTED)

    def send_command(self, command: str):
        """Queue a command to be sent."""
        self.command_queue.append(command)

    def stop(self):
        """Stop the thread gracefully."""
        self.running = False
