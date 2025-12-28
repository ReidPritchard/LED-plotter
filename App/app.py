"""PolarPlot Controller - Main entry point."""

import os
import sys

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from ui.main_window import PlotterControlWindow


def main():
    """Launch the PolarPlot controller application."""
    app = QApplication(sys.argv)

    app.setApplicationDisplayName("PolarPlot Controller")
    app.setApplicationName("PolarPlotController")
    app.setOrganizationName("Good in Theory Studios")
    app.setWindowIcon(QIcon(os.path.join("assets", "app_icon.icns")))

    window = PlotterControlWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
