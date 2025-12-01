# LED Plotter (PolarPlot)

A hanging pen plotter system using polar kinematics to control a suspended drawing mechanism.

## Overview

This project consists of two main components:

1. **PyQt6 Desktop Application** - GUI controller for sending commands and visualizing plotter state
2. **Arduino Firmware** - Stepper motor control and kinematics calculations

The system uses two stepper motors mounted at fixed positions to control cable lengths, positioning a gondola/pen holder in 2D space using polar coordinates.

## Quick Start

### Python App

```bash
cd App/
pixi install              # Install dependencies
pixi run python app.py    # Launch GUI
```

### Arduino Firmware

Upload `Arduino/simple-led-plotter.ino` using Arduino IDE or arduino-cli.

**Requirements:**
- AFMotor_R4 library
- FastLED library
- Serial baud rate: 9600

## Project Structure

```
LED-plotter/
├── App/                          # PyQt6 desktop application
│   ├── app.py                    # Main entry point
│   ├── models.py                 # Data models and constants
│   ├── serial_handler.py         # Background serial communication
│   └── ui/                       # Modular UI components
├── Arduino/
│   └── simple-led-plotter.ino    # Firmware for stepper motor control
└── CLAUDE.md                     # AI assistant onboarding
```

## Features

- Serial port connection management
- Real-time position and cable length display
- Command queue visualization
- Interactive command panel (Move, Home, Test, Calibrate)
- Console output for debugging
- Synchronized stepper motor control
- EEPROM calibration storage

## Hardware

- Nema 17 stepper motors (200 steps/revolution)
- Adafruit Motor Shield R4
- WS2812 LED strip
- Physical toggle button

## Documentation

For detailed information, see:
- `CLAUDE.md` - Project-wide documentation
- `App/CLAUDE.md` - Python app development guidelines

## License

Educational project for Creative Code coursework.
