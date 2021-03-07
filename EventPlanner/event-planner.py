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
            self.read_from_db(db_file)

    def create_ui(self):
        """Set up the user interface, signals
        """
        self.widget = QtWidgets.QWidget(self)
        self.setCentralWidget(self.widget)

        self.matchstable = QtWidgets.QTableWidget(0, 4)
        self.matchstable.setHorizontalHeaderLabels(['Red', 'Red', 'Blue', 'Blue'])
        header = self.matchstable.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.Stretch)

        self.vboxlayout = QtWidgets.QVBoxLayout()
        self.vboxlayout.addWidget(self.matchstable, stretch=10)

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

        self.update_ui()

    def reset(self):
        """ Reset
        """
        self.quals = []
        self.teams = []
        for row_no in range(self.matchstable.rowCount()):
            self.eventstable.removeRow(0)
        pass

    def open_file(self):
        """Open a db file
        """

        dialog_txt = "Choose FTC Score Keeper db file"
        filename = QtWidgets.QFileDialog.getOpenFileName(self, dialog_txt, os.path.expanduser('~'), "DB Files (*.db)")
        if not filename:
            return

        # getOpenFileName returns a tuple, so use only the actual file name
        self.read_from_db(filename[0])

    def get_team_info(self, team_number):
        for row in self.teams:
            if row['number'] == team_number:
                return row
        raise Exception(f'Team {team_number} not found')

    def read_from_db(self, filename):
        self.db_file = filename
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        self.reset()
        cur = conn.cursor()
        result = cur.execute("SELECT * FROM quals")
        self.quals = result.fetchall()
        result = cur.execute("SELECT * FROM teamInfo")
        self.teams = result.fetchall()
        conn.close()
        row_no = 0
        for match in self.quals:
            self.matchstable.insertRow(row_no)
            self.matchstable.setVerticalHeaderItem(row_no, QtWidgets.QTableWidgetItem(f'#{match["match"]}'))
            team = self.get_team_info(match['red1'])
            item = QtWidgets.QTableWidgetItem(f"{team['number']} : {team['name']}")
            item.setFlags(item.flags() ^ QtCore.Qt.ItemIsEditable)
            item.setForeground(QtGui.QBrush(QtGui.QColor(QtCore.Qt.red)))
            self.matchstable.setItem(row_no, 0, item)
            team = self.get_team_info(match['red2'])
            item = QtWidgets.QTableWidgetItem(f"{team['number']} : {team['name']}")
            item.setFlags(item.flags() ^ QtCore.Qt.ItemIsEditable)
            item.setForeground(QtGui.QBrush(QtGui.QColor(QtCore.Qt.red)))
            self.matchstable.setItem(row_no, 1, item)
            team = self.get_team_info(match['blue1'])
            item = QtWidgets.QTableWidgetItem(f"{team['number']} : {team['name']}")
            item.setFlags(item.flags() ^ QtCore.Qt.ItemIsEditable)
            item.setForeground(QtGui.QBrush(QtGui.QColor(QtCore.Qt.blue)))
            self.matchstable.setItem(row_no, 2, item)
            team = self.get_team_info(match['blue2'])
            item = QtWidgets.QTableWidgetItem(f"{team['number']} : {team['name']}")
            item.setFlags(item.flags() ^ QtCore.Qt.ItemIsEditable)
            item.setForeground(QtGui.QBrush(QtGui.QColor(QtCore.Qt.blue)))
            self.matchstable.setItem(row_no, 3, item)
            row_no += 1

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
    player.resize(640, 480)
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
