# LED Plotter - AI Assistant Onboarding

## 0. Project Overview

**PolarPlot** is a hanging pen plotter control application. It controls a physical 2-motor hanging plotter system via serial communication with Arduino. The project consists of:

- **PyQt6 Desktop App (Python)**: GUI application for controlling the plotter, sending drawing commands, and visualizing plots
- **Arduino Firmware**: Manages stepper motors, kinematics, and serial command processing for a hanging plotter with polar coordinate system
- **Serial Protocol**: Text-based command interface (M x y, H, T, C, ?)

**Golden rule**: When unsure about hardware constraints, kinematics calculations, or serial protocol details, ALWAYS consult the developer rather than making assumptions that could damage the physical plotter.

---

## 1. Non-negotiable Golden Rules

| #  | AI *may* do | AI *must NOT* do |
|----|-------------|------------------|
| G-0 | Ask for clarification about hardware limits, motor specs, or physical constraints | ❌ Make assumptions about plotter dimensions, cable lengths, or motor capabilities |
| G-1 | Generate code **only inside** `App/` directory (Python GUI code) | ❌ Touch Arduino firmware without explicit permission |
| G-2 | Add/update **`AIDEV-NOTE:` anchor comments** near kinematics, serial communication, or coordinate transformation code | ❌ Delete or modify existing `AIDEV-` comments |
| G-3 | Follow PEP 8 Python style, use type hints for new code | ❌ Reformat entire files or change existing code style without request |
| G-4 | For changes >50 LOC or affecting core kinematics/serial protocol, ask for confirmation | ❌ Make large refactors to coordinate systems or motor control without guidance |
| G-5 | Stay within current task context | ❌ Continue work from prior prompts after "new task" designation |
| G-6 | Preserve physical safety constraints (movement limits, speed limits) | ❌ Remove or modify constrain() calls or safety bounds without explicit permission |

---

## 2. Build, Test & Utility Commands

```bash
# Package management (uses Pixi - conda-forge based)
pixi install                 # Install dependencies from pixi.toml
pixi add <package>           # Add new dependency
pixi run <command>           # Run command in pixi environment

# Running the application
pixi run python app.py       # Launch the PyQt6 GUI

# Arduino (when working on firmware)
# Upload via Arduino IDE or arduino-cli
# Serial monitor: 9600 baud for plotter communication
```

**Important Notes:**
- Uses **Pixi** package manager (not pip/conda directly)
- Python 3.14+ required
- PyQt6 for GUI framework
- No automated tests currently configured

---

## 3. Coding Standards

- **Language**: Python 3.14+
- **Framework**: PyQt6 for desktop GUI
- **Formatting**: PEP 8 style guide
  - 4 spaces for indentation
  - Max line length: 100 characters
  - Use type hints for function signatures
- **Typing**: Use type hints for new code, especially for coordinate/position types
- **Naming**:
  - `snake_case` for functions and variables
  - `PascalCase` for classes
  - `UPPER_CASE` for constants
- **Error Handling**:
  - Handle serial communication errors gracefully
  - Validate coordinate bounds before sending to hardware
  - Log errors for debugging without crashing GUI
- **Documentation**:
  - Docstrings for classes and non-trivial functions
  - Inline comments for kinematics/math calculations
- **Testing**: Manual testing via GUI; consider adding unit tests for coordinate transformations

**Example code pattern:**
```python
from typing import Tuple

class PlotterController:
    """Controls communication with the hanging plotter hardware."""

    MACHINE_WIDTH: float = 800.0  # mm
    MACHINE_HEIGHT: float = 600.0  # mm

    def move_to(self, x: float, y: float) -> bool:
        """
        Send absolute movement command to plotter.

        Args:
            x: X coordinate in mm (0 to MACHINE_WIDTH)
            y: Y coordinate in mm (0 to MACHINE_HEIGHT)

        Returns:
            True if command sent successfully, False otherwise
        """
        # AIDEV-NOTE: Coordinates are constrained on Arduino side, but validate here too
        x = max(50, min(x, self.MACHINE_WIDTH - 50))
        y = max(50, min(y, self.MACHINE_HEIGHT - 50))

        command = f"M {x} {y}\n"
        return self.send_command(command)
```

---

## 4. Project Layout & Core Components

| Directory/File | Description |
|----------------|-------------|
| `App/app.py` | Main application entry point - launches the GUI |
| `App/models.py` | Data classes (ConnectionState, MachineConfig, PlotterState) and constants |
| `App/serial_handler.py` | SerialThread for background serial communication |
| `App/ui/` | Modular UI components package |
| `App/ui/main_window.py` | Main window coordinator - connects all panels |
| `App/ui/connection_panel.py` | Serial port connection controls |
| `App/ui/config_panel.py` | Machine configuration (width, height, margin) |
| `App/ui/state_panel.py` | Hardware state display (position, cables, calibration) |
| `App/ui/queue_panel.py` | Command queue visualization |
| `App/ui/command_panel.py` | Command input controls (move, home, test, etc.) |
| `App/ui/console_panel.py` | Console output for serial communication |
| `App/pixi.toml` | Pixi package manager configuration |
| `App/pixi.lock` | Locked dependency versions |
| `Arduino/simple-led-plotter.ino` | Stepper motor control firmware |

**Modular Architecture:**
The app is organized into separate, reusable UI panels that can be easily rearranged or modified independently. Each panel is self-contained with its own layout and widgets, while `main_window.py` coordinates them and handles business logic.

**Key domain models/concepts:**
- **Polar/Cable Kinematics**: Hanging plotter uses cable lengths from two fixed points to determine pen position (forward/inverse kinematics)
- **Serial Protocol**: Text commands over UART (9600 baud): `M x y` (move), `H` (home), `T` (test square), `C` (calibrate), `?` (status)
- **Coordinate System**: Cartesian (X, Y) in mm, origin at top-left motor position
- **Cable Lengths**: Calculated from Cartesian position using Pythagorean theorem
- **STEPS_PER_MM**: Critical calibration value (currently 5.035) stored in Arduino EEPROM

---

## 5. Anchor Comments

Add specially formatted comments throughout the codebase for inline knowledge that can be easily searched.

### Guidelines:

- Use `AIDEV-NOTE:`, `AIDEV-TODO:`, or `AIDEV-QUESTION:` prefixes
- Keep concise (≤ 120 chars)
- Always locate existing anchors before scanning files
- Update relevant anchors when modifying code
- Don't remove `AIDEV-NOTE`s without explicit instruction
- Add anchors for code that is: complex, important, confusing, or potentially buggy

**Critical areas needing anchor comments:**
- Coordinate transformation calculations
- Serial command parsing and formatting
- Bounds checking and safety constraints
- Kinematics calculations (cable length ↔ XY position)
- Speed/acceleration control

Example:
```python
# AIDEV-NOTE: Cable lengths calculated using polar kinematics - DO NOT modify without testing
left_cable = math.sqrt(x**2 + y**2)
right_cable = math.sqrt((MACHINE_WIDTH - x)**2 + y**2)
```

---

## 6. Commit Discipline

- **Granular commits**: One logical change per commit
- **Tag AI-generated commits**: Include "🤖 AI:" prefix for AI-assisted commits
- **Clear commit messages**: Format: `<type>: <description>`
  - Types: feat, fix, refactor, docs, style, test
  - Example: `feat: add serial port selection dialog`
- **Branch strategy**: Work in feature branches, not directly on main
- **Review requirements**: Manual testing of GUI + hardware before merging

---

## 7. Serial Communication Protocol

**Arduino Command Format** (text-based, newline-terminated):
- `M <x> <y>` - Move to absolute position in mm
- `H` - Move to home position (center)
- `T` - Execute test pattern (square)
- `C` - Enter calibration mode
- `?` - Print status (position, cable lengths, steps/mm)

**Response Format**: Human-readable text over Serial at 9600 baud

**Python Implementation Pattern:**
```python
import serial

class PlotterSerial:
    def __init__(self, port: str, baudrate: int = 9600):
        # AIDEV-NOTE: 9600 baud is hardcoded in Arduino firmware
        self.ser = serial.Serial(port, baudrate, timeout=1)

    def send_command(self, command: str) -> str:
        """Send command and read response."""
        self.ser.write(command.encode('utf-8'))
        return self.ser.readline().decode('utf-8').strip()
```

**Testing approach:**
- Use Arduino Serial Monitor for direct command testing
- Test coordinate bounds before hardware testing
- Verify homing before complex movements

---

## 8. Kinematics & Coordinate Systems

The hanging plotter uses **polar kinematics** with two cable lengths determining pen position.

**Physical Setup:**
- Two stepper motors at fixed positions: (0, 0) and (MACHINE_WIDTH, 0)
- Pen/gondola hangs from cables controlled by motors
- Drawing area: 800mm × 600mm (configurable in Arduino)

**Forward Kinematics** (cable lengths → XY position):
- Complex, requires solving system of equations (not implemented in current firmware)

**Inverse Kinematics** (XY position → cable lengths):
```python
# From Arduino firmware (app.py will need equivalent)
left_cable = sqrt(x² + y²)
right_cable = sqrt((MACHINE_WIDTH - x)² + y²)
```

**Key points:**
- Coordinate (0, 0) is at left motor position
- Y-axis points downward
- Safety margins: 50mm from edges
- STEPS_PER_MM calibration is critical for accuracy

**Testing approach:**
- Test square pattern (`T` command) to verify coordinate accuracy
- Use calibration mode (`C` command) to validate STEPS_PER_MM
- Always home (`H`) before complex patterns

---

## 9. Testing Framework & Patterns

**Current State:** No automated testing framework configured

**Recommended Testing Strategy:**
- **Unit tests**: Coordinate transformation functions, bounds checking
- **Integration tests**: Serial communication mocking
- **Manual GUI tests**: All button actions, serial port selection
- **Hardware tests**: Use `T` (test square) command on actual plotter

**Example test pattern:**
```python
# Future test structure
import pytest
from plotter_controller import PlotterController

def test_coordinate_bounds():
    """Verify coordinates are constrained to safe area."""
    controller = PlotterController()

    # Test exceeding bounds
    x, y = controller.constrain_position(-10, -10)
    assert x >= 50 and y >= 50

    x, y = controller.constrain_position(900, 700)
    assert x <= 750 and y <= 550  # MACHINE_WIDTH/HEIGHT - 50
```

---

## 10. Directory-Specific Documentation

- Always check for `AGENTS.md` or `README.md` files in subdirectories
- Document significant architectural decisions in `App/AGENTS.md` if app grows complex
- Arduino firmware changes should be documented in comments due to hardware implications

---

## 11. Common Pitfalls

**Hardware-Specific:**
- **Exceeding movement bounds**: Always constrain X/Y before sending commands (50mm margin)
- **Wrong STEPS_PER_MM**: Leads to inaccurate drawings; use calibration mode
- **Serial communication errors**: Implement timeouts and error handling
- **Cable tangling**: Homing required after power cycle; validate starting position

**Software:**
- **Wrong serial baud rate**: Must be 9600 (hardcoded in Arduino)
- **Coordinate system confusion**: Remember Y-axis points downward
- **Float precision**: Use consistent precision for coordinate calculations
- **Blocking GUI**: Serial communication should be async/threaded in PyQt
- **Missing dependency manager**: Must use `pixi`, not pip directly

**Arduino/Firmware:**
- **Modifying kinematics without testing**: Can damage hardware or cause cable tangling
- **Changing motor speed without testing**: Too fast = skipped steps, too slow = inefficient
- **Removing safety constraints**: Could damage motors or plotter structure

---

## 12. Versioning Conventions

**Current Version:** 0.1.0 (from pixi.toml)

**Semantic Versioning (SemVer):**
- **MAJOR (1.0.0)**: Breaking changes to serial protocol or coordinate system
- **MINOR (0.2.0)**: New features (GUI enhancements, new drawing modes)
- **PATCH (0.1.1)**: Bug fixes, performance improvements

Update version in `pixi.toml` when releasing.

---

## 13. Key File & Pattern References

**Coordinate Transformation:**
- Location: `Arduino/simple-led-plotter.ino:60-73`
- Pattern: Pythagorean theorem for cable length calculation

**Serial Command Processing:**
- Location: `Arduino/simple-led-plotter.ino:252-287`
- Pattern: Switch-case command parser with single-letter commands

**Motor Control:**
- Location: `Arduino/simple-led-plotter.ino:75-124`
- Pattern: Synchronized stepping with proportional movement

**Calibration & EEPROM:**
- Location: `Arduino/simple-led-plotter.ino:132-218`
- Pattern: Interactive calibration with persistent storage

---

## 14. Domain-Specific Terminology

- **Gondola**: The pen holder suspended by cables
- **Cable Length**: Distance from motor to gondola (controlled by stepper motors)
- **Polar/Hanging Plotter**: Uses cable lengths (polar coordinates) instead of linear axes
- **Forward/Inverse Kinematics**: Conversion between cable lengths ↔ XY coordinates
- **STEPS_PER_MM**: Calibration constant relating motor steps to cable movement (mm)
- **Stepper Motor**: Nema 17, 200 steps/revolution
- **AFMotor_R4**: Arduino library for Adafruit Motor Shield R4
- **EEPROM**: Non-volatile memory on Arduino for storing calibration
- **Homing**: Return to center position (MACHINE_WIDTH/2, MACHINE_HEIGHT/2)
- **Pixi**: Fast package manager built on conda-forge (replaces pip/conda)

---

## 15. Files to NOT Modify Without Permission

**Critical Files:**
- `Arduino/simple-led-plotter.ino`: Hardware control - changes could damage plotter
- `App/pixi.lock`: Auto-generated dependency lock file
- `App/.gitignore`, `App/.gitattributes`: Git configuration

**Kinematics Functions (require validation before changes):**
- Lines 60-73 in Arduino firmware: `calculateCableLengths()`, `updateCableLengths()`
- Lines 75-124: `moveTo()` - core movement function with safety constraints

**When adding new files**, follow the existing structure:
- Python GUI code in `App/`
- Arduino code stays in `Arduino/`
- Use Pixi for Python dependencies, not manual pip installs

---

## AI Assistant Workflow: Step-by-Step Methodology

When responding to user instructions, follow this process:

1. **Consult Relevant Guidance**: Check this `CLAUDE.md` for task-relevant instructions
2. **Clarify Ambiguities**: Ask about hardware constraints, movement limits, or serial protocol changes
3. **Break Down & Plan**: Create plan referencing kinematics, serial protocol, and safety constraints
4. **Trivial Tasks**: Proceed immediately for simple GUI changes
5. **Non-Trivial Tasks**: Present plan for review, especially for:
   - Coordinate system changes
   - Serial protocol modifications
   - Movement/speed/acceleration changes
   - Any Arduino firmware changes
6. **Track Progress**: Use todo lists for multi-step features (e.g., "add drawing canvas with coordinate display")
7. **If Stuck, Re-plan**: Return to step 3, consult developer about hardware/physics constraints
8. **Update Documentation**: Add anchor comments for kinematics, serial code, coordinate transformations
9. **User Review**: Request testing on actual hardware before considering complete
10. **Session Boundaries**: Suggest fresh sessions for unrelated tasks (GUI work vs. firmware changes)

---

## Hardware Safety Reminders

**Before sending movement commands:**
- ✅ Verify coordinates are within bounds (50mm margins)
- ✅ Ensure plotter is homed after power cycle
- ✅ Test complex patterns in simulation/visualization first
- ✅ Keep emergency stop accessible (power off Arduino)

**Never:**
- ❌ Remove coordinate constraints without developer approval
- ❌ Modify STEPS_PER_MM without re-calibration
- ❌ Increase motor speed beyond tested limits
- ❌ Send rapid movements to opposite corners (cable stress)
