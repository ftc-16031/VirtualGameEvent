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

        self.hbuttonbox = QtWidgets.QHBoxLayout()
        self.generatebutton = QtWidgets.QPushButton("Generate Folder Skeleton ...")
        self.hbuttonbox.addWidget(self.generatebutton)
        self.generatebutton.clicked.connect(self.generate)
        self.resetbutton = QtWidgets.QPushButton("Reset")
        self.hbuttonbox.addWidget(self.resetbutton)
        self.resetbutton.clicked.connect(self.reset)

        self.vboxlayout = QtWidgets.QVBoxLayout()
        self.vboxlayout.addWidget(self.matchstable, stretch=10)
        self.vboxlayout.addLayout(self.hbuttonbox, stretch=1)

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

    def generate(self):
        """Generate skeleton folders
        """

        dialog_txt = "Choose the root folder of game files"
        filename = QtWidgets.QFileDialog.getExistingDirectory(self, dialog_txt, os.path.curdir)
        if not filename or not os.path.isdir(filename):
            return
        if os.listdir(filename):
            msgBox = QtWidgets.QMessageBox()
            msgBox.setIcon(QtWidgets.QMessageBox.Warning)
            msgBox.setText(f"The root folder [{filename}] you choose is not empty, do you want to continue?")
            msgBox.setWindowTitle("Are you sure?")
            msgBox.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            # msgBox.buttonClicked.connect(msgButtonClick)

            returnValue = msgBox.exec()
            if returnValue != QtWidgets.QMessageBox.Yes:
                return
        self.root_folder = filename

        # generate uploads folder
        upload_folder = os.path.join(self.root_folder, 'Team Uploads')
        self.ensure_folder_exists(upload_folder)
        self.create_text_file(os.path.join(upload_folder, 'Please share these folders for individual team separately!'))
        for match in self.quals:
            self.generate_team_upload_folder(match['red1'], upload_folder, match['match'], 'Red')
            self.generate_team_upload_folder(match['red2'], upload_folder, match['match'], 'Red')
            self.generate_team_upload_folder(match['blue1'], upload_folder, match['match'], 'Blue')
            self.generate_team_upload_folder(match['blue2'], upload_folder, match['match'], 'Blue')
        # generate match folder
        matches_folder = os.path.join(self.root_folder, 'Game Matches')
        self.ensure_folder_exists(matches_folder)
        for match in self.quals:
            match_folder = os.path.join(matches_folder, f'Match #{match["match"]}')
            self.ensure_folder_exists(match_folder)
            self.create_text_file(
                os.path.join(match_folder, 'Please use MatchVideoProcessor to generate Video Manifest yaml file!'))
            manifest = self.match_manifest(match)
            stream = open(os.path.join(match_folder, f'match{match["match"]}.yml'), 'w')
            yaml.safe_dump(manifest, stream)
        # generate game video folder
        output_folder = os.path.join(self.root_folder, 'Match Video Published')
        self.ensure_folder_exists(output_folder)
        self.create_text_file(os.path.join(output_folder, 'Please use GameProducer to generate the Match Videos to here!'))
        return

    def ensure_folder_exists(self, folder):
        if not os.path.exists(folder):
            os.mkdir(folder)

    def create_text_file(self, filename, content=''):
        if not os.path.exists(filename):
            f = open(filename, 'a')
            f.write(content)
            f.close()

    def generate_team_upload_folder(self, team_number, upload_folder, match_number, alliance):
        team = self.get_team_info(team_number)
        team_folder = os.path.join(upload_folder, f'{team["number"]}-{team["name"]}')
        self.ensure_folder_exists(team_folder)
        self.create_text_file(os.path.join(team_folder, 'Please upload the game video file (mp4, 480p suggested) to corresponding match folder'))
        match_folder = os.path.join(team_folder, f'Match #{match_number} {alliance} Alliance')
        self.ensure_folder_exists(match_folder)
        self.create_text_file(os.path.join(match_folder, f'Please upload the match video file of #{match_number} ({alliance} Alliance) to this folder'))

    def match_video_file_prefix(self, alliance, team_number, match_number):
        return f'match{match_number}-{alliance}-team{team_number}'

    def match_manifest(self, match):
        teams = []
        team = self.get_team_info(match['red1'])
        file_name = self.match_video_file_prefix('red', team['number'], match['match'])
        teams.append({'TeamName': team['name'], 'TeamNumber': team['number'], 'GameVideo': {'Location': f'{file_name}.mp4', 'VideoManifest': f'!include {file_name}.yml'}})
        team = self.get_team_info(match['red2'])
        file_name = self.match_video_file_prefix('red', team['number'], match['match'])
        teams.append({'TeamName': team['name'], 'TeamNumber': team['number'], 'GameVideo': {'Location': f'{file_name}.mp4', 'VideoManifest': f'!include {file_name}.yml'}})
        team = self.get_team_info(match['blue1'])
        file_name = self.match_video_file_prefix('blue', team['number'], match['match'])
        teams.append({'TeamName': team['name'], 'TeamNumber': team['number'], 'GameVideo': {'Location': f'{file_name}.mp4', 'VideoManifest': f'!include {file_name}.yml'}})
        team = self.get_team_info(match['blue2'])
        file_name = self.match_video_file_prefix('blue', team['number'], match['match'])
        teams.append({'TeamName': team['name'], 'TeamNumber': team['number'], 'GameVideo': {'Location': f'{file_name}.mp4', 'VideoManifest': f'!include {file_name}.yml'}})
        return {'VirtualGame': {'Name': f'Match #{match["match"]}', 'Teams': teams}}

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
