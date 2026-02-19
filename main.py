from PySide6.QtCore import QDir
from PySide6.QtWidgets import QApplication

from components.MainWindow import MainWindow
from utils.paths import resource_path

# from qt_material import apply_stylesheet, export_theme

if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)

    theme_dir = resource_path("theme")
    if theme_dir.exists():
        QDir.addSearchPath("icon", str(theme_dir))

    win = MainWindow()
    with open(resource_path('theme/dark_gold.qss'), 'r') as f:
        qss = f.read()
        app.setStyleSheet(qss)
    # apply_stylesheet(
    #     app,
    #     theme="theme/dark_gold.xml",
    # )
    #
    # export_theme(theme="theme/dark_gold.xml",
    #              qss="dark_gold.qss",
    #             rcc="resources.rcc",
    #             output='theme',
    #             prefix='icon:/',
    #         )

    win.show()
    sys.exit(app.exec())
