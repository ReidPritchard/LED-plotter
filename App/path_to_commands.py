"""Convert colored paths to plotter serial commands.

AIDEV-NOTE: This module generates the actual serial commands for the
Arduino plotter. Commands follow the format: M x y [r g b]
"""

import math

from models import ColoredPath, MachineConfig, RenderStyle


class PathToCommandsConverter:
    """Converts ColoredPath objects to plotter serial commands."""

    def __init__(self, machine_config: MachineConfig):
        self.machine_config = machine_config

    def path_to_commands(
        self,
        path: ColoredPath,
        include_color: bool = True,
    ) -> list[str]:
        """Convert a single path to movement commands.

        Args:
            path: ColoredPath with points and color
            include_color: Whether to include RGB in commands

        Returns:
            List of command strings (e.g., "M 200.0 300.0 255 0 0")

        AIDEV-NOTE: Each point generates a move command. LED color is
        included to enable smooth color interpolation during movement.
        """
        commands = []
        r, g, b = path.color

        for x, y in path.points:
            if include_color:
                cmd = f"M {x:.1f} {y:.1f} {r} {g} {b}"
            else:
                cmd = f"M {x:.1f} {y:.1f}"
            commands.append(cmd)

        return commands

    def paths_to_commands(
        self,
        paths: "list[ColoredPath]",
        processing_style: RenderStyle | None = None,
        include_color: bool = True,
        add_home_start: bool = True,
        add_home_end: bool = True,
    ) -> list[str]:
        """Convert multiple paths to command sequence.

        Args:
            paths: List of ColoredPath objects
            include_color: Whether to include RGB values
            add_home_start: Add home command at start
            add_home_end: Add home command at end

        Returns:
            Complete list of plotter commands

        AIDEV-NOTE: Paths should be pre-optimized for order.
        Consider grouping by color to minimize LED changes.
        """
        commands = []

        # Optional home at start
        if add_home_start:
            commands.append("H")

        # Convert each path
        if processing_style is RenderStyle.STIPPLES:
            # For stipples, we only want to move to the
            # center of each path (circle)
            for path in paths:
                if not path.points:
                    continue
                # Calculate center point
                xs = [p[0] for p in path.points]
                ys = [p[1] for p in path.points]
                center_x = sum(xs) / len(xs)
                center_y = sum(ys) / len(ys)

                r, g, b = path.color

                # Move to the center point
                # without drawing (rgb == 0,0,0)
                # then draw the stipple point by setting color
                # then turn off color again
                commands.append(f"M {center_x:.1f} {center_y:.1f} 0 0 0")
                commands.append(f"M {center_x:.1f} {center_y:.1f} {r} {g} {b}")
                commands.append(f"M {center_x:.1f} {center_y:.1f} 0 0 0")
        else:
            for path in paths:
                path_commands = self.path_to_commands(path, include_color)
                commands.extend(path_commands)

        # Optional home at end
        if add_home_end:
            commands.append("H")

        return commands

    def estimate_execution_time(
        self,
        commands: list[str],
        speed_mm_s: float | None = None,
    ) -> float:
        """Estimate total execution time in seconds.

        Args:
            commands: List of plotter commands
            speed_mm_s: Movement speed in mm/s (uses config default if None)

        Returns:
            Estimated time in seconds

        AIDEV-NOTE: Simple estimation based on total distance.
        Does not account for acceleration/deceleration.
        """
        speed = speed_mm_s or self.machine_config.speed
        if speed <= 0:
            return 0.0

        total_distance = self._calculate_total_distance(commands)
        return total_distance / speed

    def _calculate_total_distance(self, commands: list[str]) -> float:
        """Calculate total travel distance from commands."""
        total = 0.0
        prev_x, prev_y = None, None

        for cmd in commands:
            # Parse M commands
            if cmd.startswith("M "):
                parts = cmd.split()
                if len(parts) >= 3:
                    try:
                        x = float(parts[1])
                        y = float(parts[2])

                        if prev_x is not None and prev_y is not None:
                            dx = x - prev_x
                            dy = y - prev_y
                            total += math.sqrt(dx * dx + dy * dy)

                        prev_x, prev_y = x, y
                    except ValueError:
                        continue
            elif cmd == "H":
                # Home position
                home_x = self.machine_config.width / 2
                home_y = self.machine_config.height / 2

                if prev_x is not None and prev_y is not None:
                    dx = home_x - prev_x
                    dy = home_y - prev_y
                    total += math.sqrt(dx * dx + dy * dy)

                prev_x, prev_y = home_x, home_y

        return total

    def validate_commands(
        self, commands: "list[str]"
    ) -> "tuple[bool, list[str]]":
        """Validate all commands are within safe bounds.

        Args:
            commands: List of plotter commands

        Returns:
            Tuple of (all_valid, error_messages)

        AIDEV-NOTE: Critical safety check - ensure all coordinates
        are within machine safe margins.
        """
        margin = self.machine_config.safe_margin
        min_x = margin
        max_x = self.machine_config.width - margin
        min_y = margin
        max_y = self.machine_config.height - margin

        errors = []

        for i, cmd in enumerate(commands):
            if cmd.startswith("M "):
                parts = cmd.split()
                if len(parts) >= 3:
                    try:
                        x = float(parts[1])
                        y = float(parts[2])

                        if x < min_x or x > max_x:
                            errors.append(
                                f"Command {i}: X={x:.1f} out of bounds "
                                f"({min_x:.1f} to {max_x:.1f})"
                            )

                        if y < min_y or y > max_y:
                            errors.append(
                                f"Command {i}: Y={y:.1f} out of bounds "
                                f"({min_y:.1f} to {max_y:.1f})"
                            )

                        # Validate RGB if present
                        if len(parts) >= 6:
                            try:
                                r, g, b = (
                                    int(parts[3]),
                                    int(parts[4]),
                                    int(parts[5]),
                                )
                                if not (
                                    0 <= r <= 255
                                    and 0 <= g <= 255
                                    and 0 <= b <= 255
                                ):
                                    errors.append(
                                        f"Command {i}: RGB values out of "
                                        f"range (0-255)"
                                    )
                            except ValueError:
                                errors.append(
                                    f"Command {i}: Invalid RGB values"
                                )

                    except ValueError:
                        errors.append(
                            f"Command {i}: Invalid coordinate format"
                        )

        return len(errors) == 0, errors

    def optimize_path_order(
        self, paths: list[ColoredPath]
    ) -> list[ColoredPath]:
        """Reorder paths to minimize travel distance.

        Uses a simple nearest-neighbor heuristic.

        AIDEV-NOTE: This is a greedy approach. For better results,
        consider grouping by color or using 2-opt optimization.
        """
        if len(paths) <= 1:
            return paths

        optimized = []
        remaining = list(paths)

        # Start from first path
        current = remaining.pop(0)
        optimized.append(current)

        # Greedily pick nearest path
        while remaining:
            current_end = current.points[-1]
            min_dist = float("inf")
            nearest_idx = 0

            for i, path in enumerate(remaining):
                # Distance to start of this path
                path_start = path.points[0]
                dx = path_start[0] - current_end[0]
                dy = path_start[1] - current_end[1]
                dist = math.sqrt(dx * dx + dy * dy)

                if dist < min_dist:
                    min_dist = dist
                    nearest_idx = i

            current = remaining.pop(nearest_idx)
            optimized.append(current)

        return optimized
