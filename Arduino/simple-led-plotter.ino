// Hanging Pen Plotter - Basic Functionality
// Hardware: Two stepper motors (left/right)

#include "AFMotor_R4.h"
#include <EEPROM.h>
#include <FastLED.h>

// ===== CONFIGURATION =====
// Stepper motors - Nema 17 (200 steps/rev)
AF_Stepper leftMotor(200, 1);   // M1 & M2
AF_Stepper rightMotor(200, 2);  // M3 & M4

// Plotter dimensions (in mm)
const float MACHINE_WIDTH = 800.0;   // Distance between motors
const float MACHINE_HEIGHT = 600.0;  // Height of drawing area
float STEPS_PER_MM = 5.035;          // Steps per mm (calibrate this!) (1589 mm for 8000 steps)

// 8000 steps = 1589 mm
// 200 steps = 1 revolution
// (1589 mm / 8000) = 0.198625 mm per step
// 1 / 0.198625 = 5.035 steps per mm
// 200 steps (or 1 rev) = 39.73 mm per revolution (full equation: 200 * (1589 / 8000) = 39.725 mm/rev)

// EEPROM addresses
const int EEPROM_MAGIC_ADDR = 0;
const int EEPROM_STEPS_ADDR = 4;
const int EEPROM_MAGIC_VALUE = 0x42;  // Magic byte to check if EEPROM is initialized

// Current position tracking
float currentX = MACHINE_WIDTH / 2.0;  // Start at center
float currentY = MACHINE_HEIGHT / 2.0;
float leftCableLength = 0;
float rightCableLength = 0;

// LED and toggle button state
#define LED_PIN A0
#define TOGGLE_PIN A5
#define NUM_LEDS 1

CRGB leds[NUM_LEDS];
bool shouldRun = true;

// Button debouncing variables
bool lastButtonState = HIGH;
unsigned long lastDebounceTime = 0;
unsigned long debounceDelay = 50;  // 50ms debounce time

bool buttonState = HIGH;  // debounced stable state
bool lastReading = HIGH;  // last raw pin reading

// ===== SETUP =====
void setup() {
  Serial.begin(9600);
  Serial.println("Hanging LED Plotter v1.0");

  // Load calibration from EEPROM if available
  loadCalibration();

  // Configure motors
  leftMotor.setSpeed(30);  // RPM (adjust for smooth movement)
  rightMotor.setSpeed(30);

  // Calculate initial cable lengths
  updateCableLengths();

  // LED
  FastLED.addLeds<WS2812, LED_PIN, GRB>(leds, NUM_LEDS);
  FastLED.setBrightness(50);

  // Toggle Button State
  buttonState = digitalRead(TOGGLE_PIN);
  lastReading = buttonState;

  // AIDEV-NOTE: Initialize LED based on shouldRun state
  if (shouldRun) {
    leds[0] = CRGB::Blue;  // Default color when enabled (will be controlled by drawing logic)
  } else {
    leds[0] = CRGB::Black;  // LED off when disabled
  }
  FastLED.show();

  Serial.println("Ready! Commands: M x y (move), H (home), T (test), C (calibrate), ? (status)");
}

// ===== MAIN LOOP =====
void loop() {
  processButtonIn();

  // Process any serial commands
  if (Serial.available() > 0) {
    processCommand();
  }
}

// ===== BUTTON INPUT =====
void processButtonIn() {
  bool buttonReading = digitalRead(TOGGLE_PIN);

  // If raw reading changed, reset debounce timer
  if (buttonReading != lastReading) {
    lastDebounceTime = millis();
  }

  // After debounce delay, accept the new state
  if ((millis() - lastDebounceTime) > debounceDelay) {
    if (buttonReading != buttonState) {  // real state change
      buttonState = buttonReading;

      if (buttonState == LOW) {  // button pressed
        shouldRun = !shouldRun;
        Serial.print("*** TOGGLED! shouldRun = ");
        Serial.println(shouldRun ? "true" : "false");

        // AIDEV-NOTE: Update LED to reflect enabled/disabled state
        if (!shouldRun) {
          leds[0] = CRGB::Black;  // Turn off LED when disabled
        } else {
          leds[0] = CRGB::Blue;  // Default color when re-enabled (will be controlled by drawing logic)
        }
        FastLED.show();
      }
    }
  }

  // Save raw reading for next loop
  lastReading = buttonReading;
}

// ===== KINEMATICS =====
// Calculate cable lengths from X,Y position
void calculateCableLengths(float x, float y, float &leftLen, float &rightLen) {
  // Left cable: from (0, 0) to (x, y)
  leftLen = sqrt(x * x + y * y);

  // Right cable: from (MACHINE_WIDTH, 0) to (x, y)
  float dx = MACHINE_WIDTH - x;
  rightLen = sqrt(dx * dx + y * y);
}

// Update current cable lengths based on position
void updateCableLengths() {
  calculateCableLengths(currentX, currentY, leftCableLength, rightCableLength);
}

// ===== MOVEMENT FUNCTIONS =====
// Move to absolute X,Y position
void moveTo(float targetX, float targetY) {
  // AIDEV-NOTE: Prevent movement when toggle button has disabled the plotter
  if (!shouldRun) {
    Serial.println("Movement blocked - plotter is disabled. Press toggle button to enable.");
    return;
  }

  // Constrain to valid area
  targetX = constrain(targetX, 50, MACHINE_WIDTH - 50);
  targetY = constrain(targetY, 50, MACHINE_HEIGHT - 50);

  // Calculate target cable lengths
  float targetLeftLen, targetRightLen;
  calculateCableLengths(targetX, targetY, targetLeftLen, targetRightLen);

  // Calculate steps needed
  int leftSteps = (targetLeftLen - leftCableLength) * STEPS_PER_MM;
  int rightSteps = (targetRightLen - rightCableLength) * STEPS_PER_MM;

  // Determine direction
  int leftDir = (leftSteps >= 0) ? FORWARD : BACKWARD;
  int rightDir = (rightSteps >= 0) ? FORWARD : BACKWARD;

  leftSteps = abs(leftSteps);
  rightSteps = abs(rightSteps);

  // Synchronized movement (move both motors proportionally)
  int maxSteps = max(leftSteps, rightSteps);

  Serial.print("Moving to (");
  Serial.print(targetX);
  Serial.print(", ");
  Serial.print(targetY);
  Serial.print(") - Steps: L=");
  Serial.print(leftSteps);
  Serial.print(" R=");
  Serial.println(rightSteps);

  // Step both motors in sync
  for (int i = 0; i < maxSteps; i++) {
    if (i < leftSteps) {
      leftMotor.step(1, leftDir, DOUBLE);  // DOUBLE for more torque
    }
    if (i < rightSteps) {
      rightMotor.step(1, rightDir, DOUBLE);
    }
    delayMicroseconds(500);  // Speed control
  }

  // Update position
  currentX = targetX;
  currentY = targetY;
  updateCableLengths();
}

// Move home (center position)
void moveHome() {
  Serial.println("Moving home...");
  moveTo(MACHINE_WIDTH / 2.0, MACHINE_HEIGHT / 2.0);
}

// ===== CALIBRATION FUNCTIONS =====
void calibrateStepsPerMM() {
  // AIDEV-NOTE: Prevent calibration when plotter is disabled
  if (!shouldRun) {
    Serial.println("Calibration blocked - plotter is disabled. Press toggle button to enable.");
    return;
  }

  Serial.println("\n===== CALIBRATION MODE =====");
  Serial.println("This will move both motors to help you calibrate STEPS_PER_MM");
  Serial.println();

  // Move to a known starting position
  Serial.println("Moving to center position...");
  moveHome();
  delay(1000);

  // Define calibration distance (in intended mm)
  const float CALIBRATION_DISTANCE = 100.0;  // 100mm
  const int CALIBRATION_STEPS = CALIBRATION_DISTANCE * STEPS_PER_MM;

  Serial.println("Mark the current gondola position.");
  Serial.println("Press any key when ready...");
  waitForSerial();

  // Move both motors the same amount (should move roughly vertically down)
  Serial.print("Moving both motors ");
  Serial.print(CALIBRATION_STEPS);
  Serial.print(" steps (should be ");
  Serial.print(CALIBRATION_DISTANCE);
  Serial.println("mm if calibrated correctly)");

  leftMotor.step(CALIBRATION_STEPS, FORWARD, DOUBLE);
  rightMotor.step(CALIBRATION_STEPS, FORWARD, DOUBLE);

  Serial.println("\nMotors have moved!");
  Serial.println("Measure the ACTUAL distance the gondola moved (in mm).");
  Serial.println("Enter the measured distance and press Enter:");

  float measuredDistance = waitForFloat();

  if (measuredDistance > 0 && measuredDistance < 500) {
    // Calculate new STEPS_PER_MM
    float newStepsPerMM = CALIBRATION_STEPS / measuredDistance;

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

  Serial.println("\nReturning to home...");
  // Return motors to original position
  leftMotor.step(CALIBRATION_STEPS, BACKWARD, DOUBLE);
  rightMotor.step(CALIBRATION_STEPS, BACKWARD, DOUBLE);

  Serial.println("Calibration complete!\n");
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
  while (!Serial.available()) {
    delay(10);
  }
  while (Serial.available()) {
    Serial.read();  // Clear buffer
  }
}

char waitForChar() {
  while (!Serial.available()) {
    delay(10);
  }
  char c = Serial.read();
  while (Serial.available()) {
    Serial.read();  // Clear remaining buffer
  }
  return c;
}

float waitForFloat() {
  while (!Serial.available()) {
    delay(10);
  }
  float value = Serial.parseFloat();
  while (Serial.available()) {
    Serial.read();  // Clear buffer
  }
  return value;
}

// ===== COMMAND PROCESSING =====
void processCommand() {
  char cmd = Serial.read();

  switch (cmd) {
    case 'H':
    case 'h':
      moveHome();
      break;

    case 'M':
    case 'm':
      {
        // Move command: M x y
        float x = Serial.parseFloat();
        float y = Serial.parseFloat();
        moveTo(x, y);
        break;
      }

    case 'C':
    case 'c':
      calibrateStepsPerMM();
      break;

    case 'T':
    case 't':
      // Test pattern: move in a square
      testSquare();
      break;

    case '?':
      printStatus();
      break;
  }
}

// ===== TEST FUNCTIONS =====
void testSquare() {
  Serial.println("Moving in test square...");
  float cx = MACHINE_WIDTH / 2.0;
  float cy = MACHINE_HEIGHT / 2.0;
  float size = 100;

  moveTo(cx - size / 2, cy - size / 2);
  delay(500);
  moveTo(cx + size / 2, cy - size / 2);
  delay(500);
  moveTo(cx + size / 2, cy + size / 2);
  delay(500);
  moveTo(cx - size / 2, cy + size / 2);
  delay(500);
  moveTo(cx - size / 2, cy - size / 2);
  delay(500);

  moveHome();
  Serial.println("Test complete!");
}

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
  Serial.print("STEPS_PER_MM: ");
  Serial.println(STEPS_PER_MM, 4);
}
