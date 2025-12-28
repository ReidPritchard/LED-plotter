"""Convert colored paths to plotter serial commands.

AIDEV-NOTE: This module generates the actual serial commands for the
Arduino plotter. Commands follow the format: M x y [r g b]
"""

import math

import numpy as np

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

        paths = list(paths)  # Copy to avoid modifying original

        # Optimize path order
        paths = self.optimize_path_order(paths)

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

    def validate_commands(self, commands: "list[str]") -> "tuple[bool, list[str]]":
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
                                f"Command {i}: X={x:.1f} out of bounds ({min_x:.1f} to {max_x:.1f})"
                            )

                        if y < min_y or y > max_y:
                            errors.append(
                                f"Command {i}: Y={y:.1f} out of bounds ({min_y:.1f} to {max_y:.1f})"
                            )

                        # Validate RGB if present
                        if len(parts) >= 6:
                            try:
                                r, g, b = (
                                    int(parts[3]),
                                    int(parts[4]),
                                    int(parts[5]),
                                )
                                if not (0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255):
                                    errors.append(f"Command {i}: RGB values out of range (0-255)")
                            except ValueError:
                                errors.append(f"Command {i}: Invalid RGB values")

                    except ValueError:
                        errors.append(f"Command {i}: Invalid coordinate format")

        return len(errors) == 0, errors

    def optimize_path_order(self, paths: list[ColoredPath]) -> list[ColoredPath]:
        """
        Reorder paths to minimize travel distance using improved nearest-neighbor heuristic.

        Enhancements over basic greedy algorithm:
        1. Starts from path closest to machine center (typical home position)
        2. Considers reversing paths to minimize travel distance
        3. Evaluates both endpoints of each candidate path

        Args:
            paths: List of ColoredPath objects to optimize

        Returns:
            Optimized list of ColoredPath objects with minimal non-drawing travel

        AIDEV-NOTE: Path reversal significantly reduces travel. Each path is evaluated
        in both normal and reversed orientation to find the shortest connection.
        """
        if len(paths) <= 1:
            return paths

        remaining = paths.copy()

        # Start with path closest to machine center (home position)
        # This minimizes initial travel from typical starting position
        machine_center = np.array([self.machine_config.width / 2, self.machine_config.height / 2])

        # Find path with start point closest to center
        best_start_path = None
        best_start_dist = float("inf")

        for path in remaining:
            if not path.points:
                continue
            dist_to_start = np.linalg.norm(np.array(path.points[0]) - machine_center)
            dist_to_end = np.linalg.norm(np.array(path.points[-1]) - machine_center)

            # Check if starting from this path (normal or reversed) is better
            if dist_to_start < best_start_dist:
                best_start_dist = dist_to_start
                best_start_path = path

        if best_start_path is None:
            return paths

        remaining.remove(best_start_path)
        current = best_start_path
        optimized = [current]

        # Greedy nearest-neighbor with path reversal
        while remaining:
            current_end = np.array(current.points[-1])

            best_candidate = None
            best_distance = float("inf")
            best_reversed = False

            # Evaluate all remaining paths in both orientations
            for candidate in remaining:
                if not candidate.points:
                    continue

                candidate_start = np.array(candidate.points[0])
                candidate_end = np.array(candidate.points[-1])

                # Distance if we connect to the start (normal orientation)
                dist_to_start = np.linalg.norm(candidate_start - current_end)

                # Distance if we connect to the end (requires reversing path)
                dist_to_end = np.linalg.norm(candidate_end - current_end)

                # Choose the orientation with minimum travel distance
                if dist_to_start < best_distance:
                    best_distance = dist_to_start
                    best_candidate = candidate
                    best_reversed = False

                if dist_to_end < best_distance:
                    best_distance = dist_to_end
                    best_candidate = candidate
                    best_reversed = True

            if best_candidate is None:
                # No valid candidates found, add remaining paths as-is
                optimized.extend(remaining)
                break

            remaining.remove(best_candidate)

            # Reverse the path if that provides a shorter connection
            if best_reversed:
                best_candidate = ColoredPath(
                    points=best_candidate.points[::-1], color=best_candidate.color
                )

            optimized.append(best_candidate)
            current = best_candidate

        return optimized
