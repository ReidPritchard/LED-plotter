// Patched Hanging LED Plotter firmware
// Adds robust serial handling for high-throughput queued commands
// - Uses fixed-size buffers (no Strings) to avoid heap fragmentation
// - Replies: OK / BUSY / ERR
// - Rejects commands while movement is active
// - Purges serial buffer during long blocking movement to avoid UART overflow
// - Fixed: Rounding error accumulation in moveTo() interpolation

#include "AFMotor_R4.h"
#include <EEPROM.h>
#include <FastLED.h>
#include <math.h>

// ===== CONFIGURATION =====
// Stepper motors - Nema 17 (200 steps/rev)
AF_Stepper leftMotor(200, 1);   // M1 & M2
AF_Stepper rightMotor(200, 2);  // M3 & M4

// Plotter dimensions (in mm)
const float MACHINE_WIDTH = 920.0;   // Distance between motors
const float MACHINE_HEIGHT = 600.0;  // Height of drawing area
float STEPS_PER_MM = 5.035;          // Steps per mm (calibrate this!)

// EEPROM addresses
const int EEPROM_MAGIC_ADDR = 0;
const int EEPROM_STEPS_ADDR = 4;
const int EEPROM_MAGIC_VALUE = 0x42;  // Magic byte to check if EEPROM is initialized

// Current position tracking
float currentX = MACHINE_WIDTH / 2.0;  // Start at center
float currentY = MACHINE_HEIGHT / 2.0;
float leftCableLength = 0;
float rightCableLength = 0;

// AIDEV-NOTE: LED color state for interpolation during movement
CRGB currentColor = CRGB::Blue;
CRGB targetColor = CRGB::Blue;
bool useColorInterpolation = false;

// LED and toggle button state
#define LED_PIN A0
#define TOGGLE_PIN A5
#define NUM_LEDS 1

CRGB leds[NUM_LEDS];
bool shouldRun = true;

// Button debouncing variables
bool buttonState = HIGH;  // debounced stable state
bool lastReading = HIGH;  // last raw pin reading
unsigned long lastDebounceTime = 0;
unsigned long debounceDelay = 50;  // 50ms debounce time

// ===== SERIAL / COMMAND BUFFER =====
#define CMD_BUFFER_SIZE 96   // safe upper bound for one command line
char cmdBuffer[CMD_BUFFER_SIZE];
uint8_t cmdIndex = 0;

// Movement guard (prevents processing of commands while moving)
volatile bool isMoving = false;

// Safety: limit durations for blocking waits in millis to allow platform to remain responsive
// (not strictly required, but a good practice on some boards)
#define YIELD_INTERVAL_MS 5

// ===== SETUP =====
void setup() {
  Serial.begin(9600);
  Serial.println("Hanging LED Plotter v2 (patched) - ready");

  // Load calibration from EEPROM if available
  loadCalibration();

  // Configure motors
  leftMotor.setSpeed(400);  // RPM (adjust for smooth movement)
  rightMotor.setSpeed(400);

  // Calculate initial cable lengths
  updateCableLengths();

  // LED
  FastLED.addLeds<WS2812, LED_PIN, GRB>(leds, NUM_LEDS);
  FastLED.setBrightness(50);

  // Toggle Button: use INPUT_PULLUP for reliable reads
  pinMode(TOGGLE_PIN, INPUT_PULLUP);
  lastReading = digitalRead(TOGGLE_PIN);
  buttonState = lastReading;

  // Initialize LED based on shouldRun state
  if (shouldRun) {
    leds[0] = currentColor;
  } else {
    leds[0] = CRGB::Black;
  }
  FastLED.show();

  Serial.println("Ready! Commands:");
  Serial.println("  M X.. Y.. [R.. G.. B..] - Move (with optional color interpolation)");
  Serial.println("  H - Home");
  Serial.println("  C - Calibrate");
  Serial.println("  ? - Status");
}

// ===== MAIN LOOP =====
void loop() {
  processButtonIn();

  // Read incoming serial bytes and build lines in cmdBuffer
  // Process all complete lines available in the hardware buffer
  while (Serial.available()) {
    char c = (char)Serial.read();

    // Ignore stray nulls
    if (c == '\0') continue;

    // newline or carriage return marks end of line
    if (c == '\n' || c == '\r') {
      if (cmdIndex > 0) {
        cmdBuffer[cmdIndex] = '\0';
        handleCommand(cmdBuffer);
        cmdIndex = 0;
      } else {
        // empty line - ignore
      }
    } else {
      // append if space remains (avoid overflow)
      if (cmdIndex < CMD_BUFFER_SIZE - 1) {
        cmdBuffer[cmdIndex++] = c;
      } else {
        // buffer overflow: drop the rest of this line and respond with ERR
        cmdIndex = 0;
        Serial.println("ERR");
        // drain until newline to resync
        while (Serial.available()) {
          char d = (char)Serial.read();
          if (d == '\n' || d == '\r') break;
        }
      }
    }
  }

  // minimal idle work
  delay(1);
}

// ===== BUTTON INPUT =====
void processButtonIn() {
  bool buttonReading = digitalRead(TOGGLE_PIN);

  if (buttonReading != lastReading) {
    lastDebounceTime = millis();
  }

  if ((millis() - lastDebounceTime) > debounceDelay) {
    if (buttonReading != buttonState) {
      buttonState = buttonReading;

      // Active-low button (pressed == LOW) when using INPUT_PULLUP
      if (buttonState == LOW) {
        shouldRun = !shouldRun;
        Serial.print("*** TOGGLED! shouldRun = ");
        Serial.println(shouldRun ? "true" : "false");

        if (!shouldRun) {
          leds[0] = CRGB::Black;
        } else {
          leds[0] = currentColor;
        }
        FastLED.show();
      }
    }
  }

  lastReading = buttonReading;
}

// ===== KINEMATICS =====
void calculateCableLengths(float x, float y, float &leftLen, float &rightLen) {
  leftLen = sqrt(x * x + y * y);
  float dx = MACHINE_WIDTH - x;
  rightLen = sqrt(dx * dx + y * y);
}

void updateCableLengths() {
  calculateCableLengths(currentX, currentY, leftCableLength, rightCableLength);
}

CRGB interpolateColor(CRGB startColor, CRGB endColor, float progress) {
  if (progress < 0.0) progress = 0.0;
  if (progress > 1.0) progress = 1.0;

  uint8_t r = (uint8_t)((float)startColor.r + (endColor.r - startColor.r) * progress);
  uint8_t g = (uint8_t)((float)startColor.g + (endColor.g - startColor.g) * progress);
  uint8_t b = (uint8_t)((float)startColor.b + (endColor.b - startColor.b) * progress);

  return CRGB(r, g, b);
}

// ===== MOVEMENT FUNCTIONS =====
// Move to absolute X,Y position using straight-line interpolation
// Returns true if movement completed, false if blocked
bool moveTo(float targetX, float targetY) {
  if (!shouldRun) {
    Serial.println("Movement blocked - plotter is disabled. Press toggle button to enable.");
    return false;
  }

  // Constrain target to safe drawing area
  if (targetX < 50) targetX = 50;
  if (targetX > MACHINE_WIDTH - 50) targetX = MACHINE_WIDTH - 50;
  if (targetY < 50) targetY = 50;
  if (targetY > MACHINE_HEIGHT - 50) targetY = MACHINE_HEIGHT - 50;

  // Compute deltas
  float dx = targetX - currentX;
  float dy = targetY - currentY;
  float dist = sqrt(dx * dx + dy * dy);

  if (dist < 0.01f) {
    // No motion needed, but still finalize LED color if interpolating
    if (useColorInterpolation) {
      currentColor = targetColor;
      leds[0] = currentColor;
      FastLED.show();
    }
    return true;
  }

  // Total number of interpolation steps (resolution)
  // 0.25–0.5 mm segments = smooth straight path
  const float SEGMENT_MM = 0.35f;
  long steps = max(1L, (long)(dist / SEGMENT_MM));

  Serial.print("Straight-line move to (");
  Serial.print(targetX);
  Serial.print(", ");
  Serial.print(targetY);
  Serial.print(") using ");
  Serial.print(steps);
  Serial.println(" interpolation steps.");

  isMoving = true;
  unsigned long lastYield = millis();

  // Track ACTUAL stepped cable lengths to carry forward rounding errors.
  // This prevents cumulative drift from discarded fractional steps.
  float actualLeft = leftCableLength;
  float actualRight = rightCableLength;

  for (long i = 0; i <= steps; i++) {
    float t = (float)i / (float)steps;

    // XY position along straight line
    float x = currentX + dx * t;
    float y = currentY + dy * t;

    // Target cable lengths for this interpolation point
    float L, R;
    calculateCableLengths(x, y, L, R);

    // Delta from ACTUAL achieved position (not target)
    // This ensures rounding remainders accumulate properly
    float dL = L - actualLeft;
    float dR = R - actualRight;

    // Compute required steps for each cable
    int leftStepCount = (int)round(dL * STEPS_PER_MM);
    int rightStepCount = (int)round(dR * STEPS_PER_MM);

    // LED color interpolation
    if (useColorInterpolation) {
      CRGB interpolated = interpolateColor(currentColor, targetColor, t);
      leds[0] = interpolated;
      FastLED.show();
    }

    // LEFT motor stepping
    if (leftStepCount != 0) {
      int dir = (leftStepCount > 0) ? FORWARD : BACKWARD;
      for (int s = 0; s < abs(leftStepCount); s++) {
        leftMotor.step(1, dir, DOUBLE);
        delayMicroseconds(500);
      }
    }

    // RIGHT motor stepping
    if (rightStepCount != 0) {
      int dir = (rightStepCount > 0) ? FORWARD : BACKWARD;
      for (int s = 0; s < abs(rightStepCount); s++) {
        rightMotor.step(1, dir, DOUBLE);
        delayMicroseconds(500);
      }
    }

    // Update actual cable lengths based on steps ACTUALLY taken
    // This carries fractional remainders forward to subsequent iterations
    actualLeft += (float)leftStepCount / STEPS_PER_MM;
    actualRight += (float)rightStepCount / STEPS_PER_MM;

    // Cooperative yield for platform responsiveness
    if ((millis() - lastYield) >= YIELD_INTERVAL_MS) {
      lastYield = millis();
      yield();
    }

    // Purge serial buffer and check for abort
    while (Serial.available()) Serial.read();
    if (!shouldRun) {
      Serial.println("BUSY");
      isMoving = false;
      return false;
    }
  }

  // Finalize LED color
  if (useColorInterpolation) {
    currentColor = targetColor;
    leds[0] = currentColor;
    FastLED.show();
  }

  // Update final position and recalculate cable lengths
  currentX = targetX;
  currentY = targetY;
  updateCableLengths();

  isMoving = false;
  return true;
}

void moveHome() {
  Serial.println("Moving home...");
  moveTo(MACHINE_WIDTH / 2.0, MACHINE_HEIGHT / 2.0);
}

// ===== CALIBRATION =====
bool calibrateStepsPerMM() {
  if (!shouldRun) {
    Serial.println("Calibration blocked - plotter is disabled. Press toggle button to enable.");
    return false;
  }

  Serial.println("\n===== CALIBRATION MODE =====");
  Serial.println("This will move both motors to help you calibrate STEPS_PER_MM");
  Serial.println();

  Serial.println("Moving to center position...");
  moveHome();
  delay(1000);

  const float CALIBRATION_DISTANCE = 100.0;  // mm
  long CALIBRATION_STEPS = (long)round(CALIBRATION_DISTANCE * STEPS_PER_MM);

  Serial.println("Mark the current gondola position.");
  Serial.println("Press any key when ready...");
  waitForSerial();

  Serial.print("Moving both motors ");
  Serial.print(CALIBRATION_STEPS);
  Serial.print(" steps (should be ");
  Serial.print(CALIBRATION_DISTANCE);
  Serial.println("mm if calibrated correctly)");

  // move down (forward)
  isMoving = true;
  leftMotor.step(CALIBRATION_STEPS, FORWARD, DOUBLE);
  rightMotor.step(CALIBRATION_STEPS, FORWARD, DOUBLE);
  isMoving = false;

  Serial.println("\nMotors have moved!");
  Serial.println("Measure the ACTUAL distance the gondola moved (in mm).");
  Serial.println("Enter the measured distance and press Enter:");

  float measuredDistance = waitForFloat();

  if (measuredDistance > 0 && measuredDistance < 500) {
    float newStepsPerMM = ((float)CALIBRATION_STEPS) / measuredDistance;

    Serial.println();
    Serial.print("Current STEPS_PER_MM: ");
    Serial.println(STEPS_PER_MM, 4);
    Serial.print("New STEPS_PER_MM: ");
    Serial.println(newStepsPerMM, 4);
    Serial.print("Difference: ");
    Serial.print(((newStepsPerMM - STEPS_PER_MM) / STEPS_PER_MM) * 100.0, 2);
    Serial.println("%");

    Serial.println("\nSave this calibration? (Y/N)");
    char response = waitForChar();

    if (response == 'Y' || response == 'y') {
      STEPS_PER_MM = newStepsPerMM;
      saveCalibration();
      Serial.println("Calibration saved!");
    } else {
      Serial.println("Calibration discarded.");
    }
  } else {
    Serial.println("Invalid measurement. Calibration cancelled.");
  }

  // return motors to original position
  isMoving = true;
  leftMotor.step(CALIBRATION_STEPS, BACKWARD, DOUBLE);
  rightMotor.step(CALIBRATION_STEPS, BACKWARD, DOUBLE);
  isMoving = false;

  Serial.println("Calibration complete!\n");
  return true;
}

void saveCalibration() {
  EEPROM.write(EEPROM_MAGIC_ADDR, EEPROM_MAGIC_VALUE);
  EEPROM.put(EEPROM_STEPS_ADDR, STEPS_PER_MM);
  Serial.println("Settings saved to EEPROM");
}

void loadCalibration() {
  if (EEPROM.read(EEPROM_MAGIC_ADDR) == EEPROM_MAGIC_VALUE) {
    EEPROM.get(EEPROM_STEPS_ADDR, STEPS_PER_MM);
    Serial.print("Loaded STEPS_PER_MM from EEPROM: ");
    Serial.println(STEPS_PER_MM, 4);
  } else {
    Serial.print("Using default STEPS_PER_MM: ");
    Serial.println(STEPS_PER_MM, 4);
    Serial.println("Run calibration (C) to set accurate value");
  }
}

// ===== HELPER FUNCTIONS =====
void waitForSerial() {
  // Wait for any byte (non-blocking-ish)
  while (!Serial.available()) {
    delay(10);
  }
  // flush current buffer
  while (Serial.available()) Serial.read();
}

char waitForChar() {
  while (!Serial.available()) {
    delay(10);
  }
  // return first available char
  char c = (char)Serial.read();
  // clear remaining bytes on that line
  while (Serial.available()) Serial.read();
  return c;
}

float waitForFloat() {
  while (!Serial.available()) {
    delay(10);
  }
  float val = Serial.parseFloat();
  while (Serial.available()) Serial.read();
  return val;
}

// ===== COMMAND PROCESSING - SAFE C-style parsing =====
void handleCommand(const char *line) {
  // trim leading spaces
  while (*line == ' ' || *line == '\t') line++;

  if (*line == '\0') return;

  // if moving, reject commands early
  if (isMoving) {
    Serial.println("BUSY");
    return;
  }

  // Copy line into a mutable buffer for tokenization
  char work[CMD_BUFFER_SIZE];
  strncpy(work, line, CMD_BUFFER_SIZE);
  work[CMD_BUFFER_SIZE - 1] = '\0';

  // Extract first token (command)
  char *saveptr;
  char *token = strtok_r(work, " \t", &saveptr);
  if (token == NULL) {
    Serial.println("ERR");
    return;
  }

  // Uppercase first token for case-insensitive comparison
  for (char *p = token; *p; ++p) *p = toupper(*p);

  if (strcmp(token, "H") == 0 || strcmp(token, "G28") == 0) {
    // Home
    moveHome();
    Serial.println("OK");
    return;
  }

  if (strcmp(token, "M") == 0 || strcmp(token, "G00") == 0 || strcmp(token, "G01") == 0) {
    // Move - parse remaining tokens/params. We'll accept flexible formats:
    // M X123 Y456 R255 G0 B128   or   M 123 456 255 0 128
    float targetX = currentX;
    float targetY = currentY;
    int r = -1, g = -1, b = -1;
    bool hasX = false, hasY = false;

    // Re-tokenize remaining input by spaces
    char *param;
    while ((param = strtok_r(NULL, " \t,", &saveptr)) != NULL) {
      // handle tokens that start with a letter (X/Y/R/G/B)
      if ((param[0] == 'X' || param[0] == 'x') && strlen(param) > 1) {
        targetX = atof(param + 1);
        hasX = true;
      } else if ((param[0] == 'Y' || param[0] == 'y') && strlen(param) > 1) {
        targetY = atof(param + 1);
        hasY = true;
      } else if ((param[0] == 'R' || param[0] == 'r') && strlen(param) > 1) {
        r = atoi(param + 1);
      } else if ((param[0] == 'G' || param[0] == 'g') && strlen(param) > 1) {
        g = atoi(param + 1);
      } else if ((param[0] == 'B' || param[0] == 'b') && strlen(param) > 1) {
        b = atoi(param + 1);
      } else {
        // token is numeric or bare number - assign in order: X, Y, R, G, B
        // Use strtod to be robust
        char *endptr;
        double v = strtod(param, &endptr);
        if (endptr != param) {
          if (!hasX) {
            targetX = (float)v;
            hasX = true;
          } else if (!hasY) {
            targetY = (float)v;
            hasY = true;
          } else if (r < 0) {
            r = (int)v;
          } else if (g < 0) {
            g = (int)v;
          } else if (b < 0) {
            b = (int)v;
          }
        } else {
          // unknown token - ignore it
        }
      }
    }

    if (r >= 0 && g >= 0 && b >= 0) {
      // clamp
      if (r < 0) r = 0; if (r > 255) r = 255;
      if (g < 0) g = 0; if (g > 255) g = 255;
      if (b < 0) b = 0; if (b > 255) b = 255;
      targetColor = CRGB((uint8_t)r, (uint8_t)g, (uint8_t)b);
      useColorInterpolation = true;
    } else {
      useColorInterpolation = false;
    }

    if (moveTo(targetX, targetY)) {
      Serial.println("OK");
    } else {
      Serial.println("BUSY");
    }
    return;
  }

  if (strcmp(token, "C") == 0) {
    if (calibrateStepsPerMM()) {
      Serial.println("OK");
    } else {
      Serial.println("BUSY");
    }
    return;
  }

  if (strcmp(token, "?") == 0) {
    printStatus();
    Serial.println("OK");
    return;
  }

  // Unknown command
  Serial.println("ERR");
}

// ===== STATUS =====
void printStatus() {
  Serial.println("===== STATUS =====");
  Serial.print("Plotter: ");
  Serial.println(shouldRun ? "ENABLED" : "DISABLED");
  Serial.print("Position: (");
  Serial.print(currentX);
  Serial.print(", ");
  Serial.print(currentY);
  Serial.println(")");
  Serial.print("Cable lengths: L=");
  Serial.print(leftCableLength);
  Serial.print(" R=");
  Serial.println(rightCableLength);
  Serial.print("LED Color (RGB): (");
  Serial.print(currentColor.r);
  Serial.print(", ");
  Serial.print(currentColor.g);
  Serial.print(", ");
  Serial.print(currentColor.b);
  Serial.println(")");
  Serial.print("STEPS_PER_MM: ");
  Serial.println(STEPS_PER_MM, 4);
}
