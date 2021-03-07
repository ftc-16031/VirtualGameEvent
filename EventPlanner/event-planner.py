"""
Event Planner read FTC official score keeper data, generate scaffolding folder structure and template manifest files

Author: FTC team #16031 Parabellum
Date: 06 Mar 2021
"""

import platform
import os
import sys
import re
import yaml
from os import path
import sqlite3

from PySide2 import QtWidgets, QtGui, QtCore


class EventPlanner(QtWidgets.QMainWindow):

    def __init__(self, db_file=None, root_folder=None, master=None):
        QtWidgets.QMainWindow.__init__(self, master)
        self.setWindowTitle("Event Planner")
        self.showMaximized()

        self.create_ui()

        if db_file is not None:
            self.open_db(db_file)

    def create_ui(self):
        """Set up the user interface, signals
        """
        self.widget = QtWidgets.QWidget(self)
        self.setCentralWidget(self.widget)

        self.vboxlayout = QtWidgets.QVBoxLayout()

        self.widget.setLayout(self.vboxlayout)

        menu_bar = self.menuBar()

        # File menu
        file_menu = menu_bar.addMenu("File")

        # Add actions to file menu
        open_action = QtWidgets.QAction("Load FTC Score Keeper db file", self)
        close_action = QtWidgets.QAction("Close App", self)
        file_menu.addAction(open_action)
        file_menu.addAction(close_action)

        open_action.triggered.connect(self.open_file)
        close_action.triggered.connect(sys.exit)

        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(5000)
        self.timer.timeout.connect(self.update_ui)

        self.reset()

    def reset(self):
        """ Reset UI
        """
        pass

    def open_file(self):
        """Open a db file
        """

        dialog_txt = "Choose FTC Score Keeper db file"
        filename = QtWidgets.QFileDialog.getOpenFileName(self, dialog_txt, os.path.expanduser('~'), "DB Files (*.db)")
        if not filename:
            return

        # getOpenFileName returns a tuple, so use only the actual file name
        self.open_db(filename[0])

    def open_db(self, filename):
        self.db_file = filename
        self.conn = sqlite3.connect(self.db_file)
        cur = self.conn.cursor()
        r = cur.execute("SELECT * FROM quals")
        print(r.fetchone())
        pass

    def update_ui(self):
        """Updates the user interface"""
        pass


def main():
    """Entry point
    """
    app = QtWidgets.QApplication(sys.argv)
    db_file = None
    if len(sys.argv) > 1:
        filename = sys.argv[1]
        if path.isfile(filename):
            db_file = filename
        else:
            print(f'ERROR : DB file passed in [{filename}] not exists')
    player = EventPlanner(db_file=db_file)
    player.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
