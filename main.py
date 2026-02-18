from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QDir

from components.MainWindow import MainWindow
from utils.paths import resource_path

if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    win = MainWindow()
    # Load pre-generated, git-tracked QSS + icons
    QDir.addSearchPath("icon", str(resource_path("themes/qt_material_gold")))
    with open(resource_path("themes/qt_material_gold.qss"), "r") as f:
        app.setStyleSheet(f.read())
    win.show()
    sys.exit(app.exec())
