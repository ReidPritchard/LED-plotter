# LED Plotter - AI Assistant Onboarding

## Project Overview

**LED Plotter** (also called **PolarPlot**) is a hanging pen plotter system that uses polar kinematics to control a suspended drawing mechanism. The project consists of two main components:

1. **PyQt6 Desktop Application (Python)** - GUI controller for sending commands and visualizing plotter state
2. **Arduino Firmware** - Stepper motor control and kinematics calculations

The system uses two stepper motors mounted at fixed positions to control cable lengths, positioning a gondola/pen holder in 2D space using polar coordinates.

**Golden Rule**: This project interfaces with physical hardware. When unsure about movement limits, coordinate transformations, serial protocols, or any hardware constraints, ALWAYS consult the developer before making changes that could damage the plotter or cause mechanical issues.

---

## Project Structure

```
LED-plotter/
├── App/                          # PyQt6 desktop application
│   ├── app.py                    # Main entry point
│   ├── models.py                 # Data models and constants
│   ├── config_manager.py         # Configuration persistence handler
│   ├── serial_handler.py         # Background serial communication
│   ├── path_to_commands.py       # SVG path to plotter command converter
│   ├── ui/                       # Modular UI components
│   │   ├── main_window.py        # Main window coordinator
│   │   ├── workflow/             # Step-based workflow system
│   │   │   ├── central_workflow.py   # Workflow state machine
│   │   │   ├── step_bar.py           # Progress indicator
│   │   │   ├── models.py             # Workflow data models
│   │   │   └── pages/                # Workflow pages
│   │   │       ├── connect_page.py   # Serial connection step
│   │   │       ├── import_page.py    # Image import step
│   │   │       ├── preview_page.py   # Preview & rendering controls
│   │   │       ├── send_page.py      # Command sending step
│   │   │       └── dashboard_page.py # Status dashboard
│   │   ├── components/           # Reusable UI components
│   │   │   ├── stipple_controls.py   # Stippling parameter controls
│   │   │   ├── hatching_controls.py  # Hatching parameter controls
│   │   │   └── cross_hatch_controls.py # Cross-hatch controls
│   │   ├── connection_panel.py   # Serial connection controls (legacy)
│   │   ├── config_panel.py       # Machine configuration
│   │   ├── state_panel.py        # Hardware state display
│   │   ├── command_panel.py      # Command input
│   │   ├── queue_panel.py        # Command queue visualization
│   │   ├── console_panel.py      # Serial console output
│   │   ├── image_panel.py        # Image import and processing
│   │   ├── simulation.py         # Simulation canvas
│   │   ├── settings_dialog.py    # Settings dialog
│   │   ├── styles.py             # Shared UI styling
│   │   └── widgets.py            # Shared custom widgets
│   ├── image_processing/         # Image processing pipeline
│   │   ├── processor.py          # Main processing coordinator
│   │   ├── quantization.py       # Color quantization
│   │   ├── rendering.py          # Stippling/hatching rendering
│   │   ├── svg_parser.py         # SVG path parsing
│   │   └── utils.py              # Shared utilities
│   ├── assets/                   # Application assets
│   │   └── app_icon.icns         # macOS app icon
│   ├── pixi.toml                 # Pixi package manager config
│   ├── pixi.lock                 # Locked dependencies
│   ├── ruff.toml                 # Ruff linter configuration
│   ├── .pre-commit-config.yaml   # Pre-commit hooks
│   └── CLAUDE.md                 # Detailed App-specific documentation
└── Arduino/
    └── simple-led-plotter.ino    # Firmware for stepper motor control
```

---

## Quick Start

### Python App (Desktop Controller)

```bash
cd App/
pixi install              # Install dependencies
pixi run python app.py    # Launch GUI
```

**Detailed documentation**: See `App/CLAUDE.md` for comprehensive Python development guidelines.

### Arduino Firmware

```bash
# Upload using Arduino IDE or arduino-cli
# Required: AFMotor_R4 library, FastLED library
# Serial baud rate: 9600
```

---

## Implementation Status

> **Version**: 0.1.0 (early alpha) | **Last Updated**: December 28, 2025

### Core Features

| Feature | Status | Notes |
|---------|--------|-------|
| Serial connection management | ✅ Done | Threaded, async I/O |
| Real-time position display | ✅ Done | Parses Arduino responses |
| Command queue | ✅ Done | Queue/send/clear workflow |
| Dockable UI panels | ✅ Done | Flexible layout via View menu |
| Simulation canvas | ✅ Done | Visual position tracking with preview alignment |
| Configuration persistence | ✅ Done | `~/.polarplot_config.json` via config_manager |
| Inverse kinematics (Arduino) | ✅ Done | Pythagorean calculation |
| LED color interpolation | ✅ Done | `M x y r g b` command |
| EEPROM calibration storage | ✅ Done | Persists STEPS_PER_MM |
| **Workflow navigation** | ✅ Done | Step-based UI (Connect→Import→Preview→Send→Dashboard) |
| **Image import & processing** | ✅ Done | Supports PNG/JPG with modular processing pipeline |
| **SVG generation** | ✅ Done | Optimized path rendering for stippling/hatching |
| **Rendering modes** | ✅ Done | Stippling, hatching, and cross-hatching controls |
| **Pre-commit hooks** | ✅ Done | Code quality automation with Ruff |

### Not Yet Implemented

| Feature | Priority | Notes |
|---------|----------|-------|
| Forward kinematics | Low | Complex; not currently needed |
| G-code file import | Future | Currently supports images only |
| Automated testing | Medium | See App/CLAUDE.md for strategy |
| Acceleration control | Low | Currently fixed speed |
| Output upside-down fix | High | Current output is inverted (see README photos) |

### Recent Changes (December 2025)

- **Workflow navigation system** - Complete step-based workflow with visual progress indicators
- **Component-based rendering controls** - Modular UI components for stipple/hatching parameters
- **SVG optimization** - Improved path generation and rendering clarity
- **Pre-commit configuration** - Added Ruff linting automation
- **UI modernization** - Comprehensive styling system with shared widgets
- **Config management** - Centralized configuration with JSON persistence
- **Image processing pipeline** - Modularized quantization, rendering, and SVG parsing

### Development Phase

**Current**: Feature-complete alpha with working image-to-plotter pipeline
**Next**: Bug fixes (output orientation), performance optimization, testing framework

---

## Component Overview

### 1. PyQt6 Desktop Application

**Purpose**: GUI for controlling the plotter, sending commands, and monitoring state

**Key Features**:
- Serial port connection management
- Real-time position and cable length display
- Command queue visualization
- Interactive command panel (Move, Home, Test, Calibrate)
- Console output for debugging

**Tech Stack**:
- Python 3.14+
- PyQt6 (desktop GUI framework)
- PySerial (serial communication)
- Pixi (package manager - conda-forge based)

**Development Guidelines**: See `App/CLAUDE.md` for:
- Coding standards (PEP 8, type hints)
- UI component architecture
- Serial communication patterns
- Testing strategies

### 2. Arduino Firmware

**Purpose**: Low-level motor control, kinematics, and serial command processing

**Key Features**:
- Inverse kinematics (XY position → cable lengths)
- Synchronized stepper motor control
- Serial command parser
- EEPROM calibration storage
- LED status indicators
- Physical button toggle

**Hardware**:
- Nema 17 stepper motors (200 steps/revolution)
- Adafruit Motor Shield R4 (AFMotor_R4 library)
- WS2812 LED strip (FastLED library)
- Physical toggle button

**Critical Constants**:
- `MACHINE_WIDTH = 800.0` mm (distance between motors)
- `MACHINE_HEIGHT = 600.0` mm (drawing area height)
- `STEPS_PER_MM = 5.035` (calibration constant - stored in EEPROM)

---

## Serial Communication Protocol

**Connection**: UART at 9600 baud (hardcoded in Arduino)

**Command Format** (text-based, newline-terminated):

| Command | Format | Description |
|---------|--------|-------------|
| `M` | `M <x> <y>` | Move to absolute position (mm) |
| `H` | `H` | Move to home position (center) |
| `T` | `T` | Execute test pattern (square) |
| `C` | `C` | Enter interactive calibration mode |
| `?` | `?` | Print status (position, cables, steps/mm) |

**Response Format**: Human-readable text output

**Example Session**:
```
> ?
Position: (400.00, 300.00)
Left: 500.00mm, Right: 500.00mm
Steps/mm: 5.035
> M 200 200
Moving to (200.00, 200.00)
Done.
```

---

## Coordinate System & Kinematics

### Physical Setup

```
[Motor Left]                    [Motor Right]
    (0, 0) ─────── 800mm ─────── (800, 0)
        \                           /
         \    Cable Left    Cable Right
          \                       /
           \                     /
            \                   /
              \               /
                [Gondola/Pen]
                   (x, y)

```

- **Origin**: (0, 0) at left motor position
- **Y-axis**: Points downward
- **Drawing Area**: 800mm × 600mm
- **Safe Margin**: 50mm from edges (constrained in both App and Arduino)

### Inverse Kinematics (XY → Cable Lengths)

```cpp
// Arduino implementation (simple-led-plotter.ino)
leftCableLength = sqrt(x² + y²)
rightCableLength = sqrt((MACHINE_WIDTH - x)² + y²)
```

**Motor Steps**:
```cpp
stepsLeft = (newLeftCable - currentLeftCable) * STEPS_PER_MM
stepsRight = (newRightCable - currentRightCable) * STEPS_PER_MM
```

**Note**: Forward kinematics (cable lengths → XY) is complex and not currently implemented.

---

## AI Assistant Guidelines

### What You Can Do

✅ **Python App (App/ directory)**:
- Add/modify UI components
- Improve serial communication handling
- Add visualization features
- Enhance command queue management
- Improve error handling and logging
- Add configuration persistence
- Create coordinate validation utilities

✅ **Documentation**:
- Update CLAUDE.md files
- Add AIDEV-NOTE anchor comments
- Document kinematics calculations
- Clarify safety constraints

### What Requires Permission

⚠️ **Requires explicit approval**:
- Modifying Arduino firmware
- Changing coordinate system calculations
- Altering movement bounds or safety margins
- Modifying serial protocol commands
- Changing STEPS_PER_MM or calibration logic
- Adjusting motor speed/acceleration parameters

❌ **Never do without permission**:
- Remove safety constraints (bounds checking)
- Change kinematics formulas without validation
- Modify EEPROM storage format
- Send untested movement commands to hardware
- Increase motor speeds beyond tested limits

### Anchor Comments

Use specially formatted comments for critical code:

```python
# AIDEV-NOTE: Cable lengths use Pythagorean theorem - verify before changes
left_cable = math.sqrt(x**2 + y**2)
```

```cpp
// AIDEV-NOTE: Safety margin prevents cable tangling and motor strain
x = constrain(x, SAFE_MARGIN, MACHINE_WIDTH - SAFE_MARGIN);
```

**When to add anchors**:
- Coordinate transformations
- Kinematics calculations
- Serial command parsing/formatting
- Bounds checking and safety constraints
- Calibration and EEPROM operations
- Motor control synchronization

---

## Common Development Tasks

### Adding New GUI Features

1. Read `App/CLAUDE.md` for detailed Python guidelines
2. Create new panel in `App/ui/` if needed
3. Follow existing modular UI pattern
4. Update `main_window.py` to integrate new component
5. Test with serial communication to actual hardware

### Modifying Movement Commands

1. **STOP**: Consult developer about hardware implications
2. Update Arduino firmware if needed
3. Update Python command generation
4. Test coordinate bounds extensively
5. Validate on hardware before merging

### Adding New Serial Commands

1. Design command format (keep simple, text-based)
2. Update Arduino command parser
3. Update Python command methods
4. Document in both CLAUDE.md files
5. Test extensively with hardware

### Calibration Changes

1. **STOP**: Calibration affects physical accuracy
2. Consult developer about calibration procedure
3. Test with known distances (e.g., 100mm movements)
4. Verify EEPROM storage works correctly

---

## Hardware Safety Checklist

Before modifying movement code, verify:

- ✅ Coordinates constrained to safe area (50mm margins)
- ✅ Cable length calculations are mathematically correct
- ✅ Movement speed is within tested limits
- ✅ No rapid corner-to-corner movements (cable stress)
- ✅ Homing sequence works after power cycle
- ✅ Emergency stop accessible (power off Arduino)

---

## Development Workflow

### For Python App Changes

1. Read `App/CLAUDE.md` for detailed guidelines
2. Use Pixi for package management (`pixi add <package>`)
3. Follow modular UI component pattern
4. Add type hints to new code
5. Test with mock serial port or actual hardware
6. Commit with clear messages (see `App/CLAUDE.md`)

### For Arduino Changes

1. **Ask first**: Hardware changes have physical consequences
2. Understand kinematics and coordinate systems
3. Test calculations manually before uploading
4. Use Serial Monitor for debugging (9600 baud)
5. Verify calibration after changes
6. Document changes in comments

### For Documentation

1. Update relevant CLAUDE.md file(s)
2. Add/update AIDEV-NOTE comments
3. Document hardware constraints clearly
4. Include examples for complex operations

---

## Troubleshooting

### Common Issues

**Serial Connection**:
- Verify baud rate is 9600
- Check correct USB port selected
- Ensure no other programs using serial port
- Reset Arduino if unresponsive

**Movement Issues**:
- Run `H` (home) command after power cycle
- Verify coordinates within bounds
- Check STEPS_PER_MM calibration
- Test with `T` (test square) command

**Calibration**:
- Use `C` command for interactive calibration
- Measure actual movement vs. commanded movement
- STEPS_PER_MM stored in EEPROM (persists across reboots)
- Current value: 5.035 (based on 8000 steps = 1589mm)

**GUI Issues**:
- Check Python version (3.14+ required)
- Verify Pixi environment: `pixi run python --version`
- Review console output for serial errors
- Check Qt event loop not blocked by serial I/O

---

## Domain-Specific Terminology

- **Gondola**: The pen holder suspended by cables
- **Polar/Hanging Plotter**: Uses cable lengths (polar coordinates) vs. linear axes (Cartesian)
- **Inverse Kinematics**: XY position → cable lengths (implemented)
- **Forward Kinematics**: Cable lengths → XY position (not implemented)
- **STEPS_PER_MM**: Calibration relating motor steps to cable movement
- **Homing**: Return to center position (MACHINE_WIDTH/2, MACHINE_HEIGHT/2)
- **Cable Length**: Distance from motor to gondola (controlled by steppers)
- **AFMotor_R4**: Adafruit Motor Shield library for Arduino
- **Pixi**: Fast conda-forge package manager (replaces pip/conda)

---

## File Modification Rules

### Safe to Modify (with guidelines)

- `App/**/*.py` - Python application code (see `App/CLAUDE.md`)
- `App/CLAUDE.md` - Python-specific documentation
- `CLAUDE.md` - Project-wide documentation

### Requires Explicit Permission

- `Arduino/simple-led-plotter.ino` - Hardware control firmware
- Kinematics functions (lines with cable length calculations)
- Safety constraints (`constrain()` calls, bound checks)
- Calibration logic (EEPROM operations)

### Never Modify

- `App/pixi.lock` - Auto-generated lock file
- `App/.gitignore`, `App/.gitattributes` - Git configuration

---

## Additional Resources

- **Detailed App Documentation**: `App/CLAUDE.md`
- **Python GUI Code**: `App/ui/*.py`
- **Arduino Firmware**: `Arduino/simple-led-plotter.ino`
- **Models & Constants**: `App/models.py`

---

## Questions?

When in doubt:
1. Check this CLAUDE.md for project-wide guidance
2. Check `App/CLAUDE.md` for Python-specific details
3. Ask the developer about hardware constraints, kinematics, or safety concerns

**Remember**: This is a physical system. Code changes can have real-world consequences. Safety and accuracy are paramount.
