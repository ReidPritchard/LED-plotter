"""PolarPlot Controller - Main entry point."""

import sys

from PyQt6.QtWidgets import QApplication

from ui.main_window import PlotterControlWindow


def main():
    """Launch the PolarPlot controller application."""
    app = QApplication(sys.argv)

    window = PlotterControlWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
