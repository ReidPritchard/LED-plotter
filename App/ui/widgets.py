"""Widget factory for creating common UI patterns with reduced boilerplate.

This module provides factory functions to eliminate repetitive widget creation
code throughout the UI components.
"""

from typing import Optional, Tuple
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDoubleSpinBox,
    QSpinBox,
    QSlider,
    QLabel,
    QHBoxLayout,
    QWidget,
    QGroupBox,
)


class WidgetFactory:
    """Factory class for creating commonly used widget patterns."""

    @staticmethod
    def create_double_spinbox(
        range_min: float,
        range_max: float,
        value: float,
        suffix: str = "",
        decimals: int = 1,
        step: float = 1.0,
        tooltip: str = "",
    ) -> QDoubleSpinBox:
        """Create a configured QDoubleSpinBox.

        Args:
            range_min: Minimum value
            range_max: Maximum value
            value: Initial value
            suffix: Suffix text (e.g., " mm", " mm/s")
            decimals: Number of decimal places
            step: Single step increment
            tooltip: Tooltip text

        Returns:
            Configured QDoubleSpinBox
        """
        spinbox = QDoubleSpinBox()
        spinbox.setRange(range_min, range_max)
        spinbox.setValue(value)
        spinbox.setSuffix(suffix)
        spinbox.setDecimals(decimals)
        spinbox.setSingleStep(step)
        if tooltip:
            spinbox.setToolTip(tooltip)
        return spinbox

    @staticmethod
    def create_int_spinbox(
        range_min: int,
        range_max: int,
        value: int,
        suffix: str = "",
        step: int = 1,
        tooltip: str = "",
    ) -> QSpinBox:
        """Create a configured QSpinBox.

        Args:
            range_min: Minimum value
            range_max: Maximum value
            value: Initial value
            suffix: Suffix text
            step: Single step increment
            tooltip: Tooltip text

        Returns:
            Configured QSpinBox
        """
        spinbox = QSpinBox()
        spinbox.setRange(range_min, range_max)
        spinbox.setValue(value)
        spinbox.setSuffix(suffix)
        spinbox.setSingleStep(step)
        if tooltip:
            spinbox.setToolTip(tooltip)
        return spinbox

    @staticmethod
    def create_slider_with_label(
        range_min: int,
        range_max: int,
        value: int,
        label_width: int = 40,
        label_format: str = "{}",
        tick_interval: Optional[int] = None,
        orientation: Qt.Orientation = Qt.Orientation.Horizontal,
        tooltip: str = "",
    ) -> Tuple[QSlider, QLabel]:
        """Create a slider with an auto-updating value label.

        The label automatically updates when the slider value changes.

        Args:
            range_min: Minimum slider value
            range_max: Maximum slider value
            value: Initial value
            label_width: Minimum width for label
            label_format: Format string for label (use {} for value placeholder)
            tick_interval: Tick mark interval (None = no ticks)
            orientation: Slider orientation
            tooltip: Tooltip text

        Returns:
            Tuple of (slider, label)
        """
        slider = QSlider(orientation)
        slider.setRange(range_min, range_max)
        slider.setValue(value)
        if tooltip:
            slider.setToolTip(tooltip)

        if tick_interval:
            slider.setTickPosition(QSlider.TickPosition.TicksBelow)
            slider.setTickInterval(tick_interval)

        label = QLabel(label_format.format(value))
        label.setMinimumWidth(label_width)

        # Auto-connect slider to label
        slider.valueChanged.connect(lambda v: label.setText(label_format.format(v)))

        return slider, label

    @staticmethod
    def create_labeled_row(
        label_text: str,
        widget: QWidget,
        stretch_after: bool = False,
    ) -> QHBoxLayout:
        """Create a horizontal layout with label and widget.

        Args:
            label_text: Text for the label
            widget: Widget to place after label
            stretch_after: Whether to add stretch after widget

        Returns:
            QHBoxLayout with label and widget
        """
        layout = QHBoxLayout()
        layout.addWidget(QLabel(label_text))
        layout.addWidget(widget)
        if stretch_after:
            layout.addStretch()
        return layout


class CollapsibleGroupBox(QGroupBox):
    """A QGroupBox that can be collapsed/expanded by clicking its title.

    The group box uses Qt's built-in checkable feature to provide
    collapse/expand functionality. When unchecked, the content is
    hidden and the box shrinks to just the title bar.
    """

    def __init__(self, title: str = "", parent: Optional[QWidget] = None):
        """Initialize collapsible group box.

        Args:
            title: Title text for the group box
            parent: Parent widget
        """
        super().__init__(title, parent)
        self.setCheckable(True)
        self.setChecked(True)  # Start expanded
        self.toggled.connect(self._on_toggled)

    def _on_toggled(self, checked: bool):
        """Handle collapse/expand when checkbox is toggled.

        Args:
            checked: True if expanded, False if collapsed
        """
        # Show/hide content based on checked state
        layout = self.layout()
        if layout:
            for i in range(layout.count()):
                item = layout.itemAt(i)
                if item:
                    widget = item.widget()
                    if widget:
                        widget.setVisible(checked)

        # Adjust height constraints
        if checked:
            self.setMaximumHeight(16777215)  # Qt's default QWIDGETSIZE_MAX
        else:
            self.setMaximumHeight(30)  # Just show title bar
