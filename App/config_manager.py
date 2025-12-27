"""Configuration persistence manager for the LED-plotter application.

This module handles loading and saving of machine configuration to/from JSON files.
"""

import json
from dataclasses import asdict
from pathlib import Path
from typing import Optional, Tuple

from models import MachineConfig, CONFIG_FILE


class ConfigManager:
    """Handles loading and saving of machine configuration."""

    def __init__(self, config_path: Path = CONFIG_FILE):
        """Initialize config manager.

        Args:
            config_path: Path to configuration file (defaults to ~/.polarplot_config.json)
        """
        self.config_path = config_path

    def load(self) -> MachineConfig:
        """Load configuration from file, returning defaults if not found.

        Returns:
            MachineConfig with loaded or default values
        """
        config = MachineConfig()

        try:
            if self.config_path.exists():
                with open(self.config_path, "r") as f:
                    data = json.load(f)
                    # Update config with loaded values (fallback to defaults)
                    config.width = data.get("width", config.width)
                    config.height = data.get("height", config.height)
                    config.safe_margin = data.get("safe_margin", config.safe_margin)
                    config.led_enabled = data.get("led_enabled", config.led_enabled)
                    config.led_brightness = data.get("led_brightness", config.led_brightness)
                    config.steps_per_mm = data.get("steps_per_mm", config.steps_per_mm)
                    config.microstepping = data.get("microstepping", config.microstepping)
                    config.speed = data.get("speed", config.speed)
                    config.acceleration = data.get("acceleration", config.acceleration)
                print(f"✓ Loaded configuration from {self.config_path}")
        except Exception as e:
            print(f"Warning: Could not load config file: {e}")

        return config

    def save(self, config: MachineConfig) -> Tuple[bool, Optional[str]]:
        """Save configuration to file.

        Args:
            config: MachineConfig to save

        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        try:
            with open(self.config_path, "w") as f:
                json.dump(asdict(config), f, indent=2)
            return True, None
        except Exception as e:
            return False, str(e)
