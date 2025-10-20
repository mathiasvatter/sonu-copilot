from PySide6.QtWidgets import QApplication

from components.MainWindow import MainWindow
from qt_material import apply_stylesheet

if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    win = MainWindow()
    apply_stylesheet(app, theme='dark_teal.xml', extra={
        'QTMATERIAL_PRIMARY_COLOR': '#ffffff',
    })
    win.show()
    sys.exit(app.exec())
