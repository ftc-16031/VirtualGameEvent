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
import shutil

from PySide2 import QtWidgets, QtGui, QtCore


class EventPlanner(QtWidgets.QMainWindow):

    def __init__(self, db_file=None, root_folder=None, master=None):
        QtWidgets.QMainWindow.__init__(self, master)
        self.setWindowTitle("Event Planner")
        self.showMaximized()

        self.root_folder = None

        self.create_ui()

        if db_file is not None:
            self.read_from_db(db_file)

        # TODO validate the root folder
        self.root_folder = root_folder

        self.update_ui()

    def create_ui(self):
        """Set up the user interface, signals
        """
        self.widget = QtWidgets.QWidget(self)
        self.setCentralWidget(self.widget)

        self.matchstable = QtWidgets.QTableWidget(0, 11)
        self.matchstable.setHorizontalHeaderLabels(['Red', 'Action', 'Red', 'Action', 'Score', 'Blue', 'Action', 'Blue', 'Action', 'Score', 'Video'])
        header = self.matchstable.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(6, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(7, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(8, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(9, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(10, QtWidgets.QHeaderView.ResizeToContents)

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
        self.timer.start()

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

    FOLDER_TEAM = 'Team Uploads'
    FOLDER_MATCH = 'Game Matches'
    FOLDER_PUBLISHED = 'Match Video Published'

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
        upload_folder = os.path.join(self.root_folder, self.FOLDER_TEAM)
        self.ensure_folder_exists(upload_folder)
        self.create_text_file(os.path.join(upload_folder, 'Please share these folders for individual team separately!'))
        for match in self.quals:
            self.generate_team_upload_folder(match['red1'], upload_folder, match['match'], 'Red')
            self.generate_team_upload_folder(match['red2'], upload_folder, match['match'], 'Red')
            self.generate_team_upload_folder(match['blue1'], upload_folder, match['match'], 'Blue')
            self.generate_team_upload_folder(match['blue2'], upload_folder, match['match'], 'Blue')
        # generate match folder
        matches_folder = os.path.join(self.root_folder, self.FOLDER_MATCH)
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
        output_folder = os.path.join(self.root_folder, self.FOLDER_PUBLISHED)
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

    def match_upload_folder(self, upload_folder, team_number, team_name, match_number, alliance):
        team_folder = os.path.join(upload_folder, f'{team_number}-{team_name}')
        match_folder = os.path.join(team_folder, f'Match #{match_number} {alliance} Alliance')
        return team_folder, match_folder

    def generate_team_upload_folder(self, team_number, upload_folder, match_number, alliance):
        team = self.get_team_info(team_number)
        team_folder, match_folder = self.match_upload_folder(upload_folder, team["number"], team["name"], match_number, alliance)
        self.ensure_folder_exists(team_folder)
        self.create_text_file(os.path.join(team_folder, 'Please upload the game video file (mp4, 480p suggested) to corresponding match folder'))
        self.ensure_folder_exists(match_folder)
        self.create_text_file(os.path.join(match_folder, f'Please upload the match video file of #{match_number} ({alliance} Alliance) to this folder'))

    def match_video_file_prefix(self, alliance, team_number, match_number):
        return f'match{match_number}-{alliance}-team{team_number}'

    def match_manifest(self, match):
        match_folder = os.path.join(self.root_folder, self.FOLDER_MATCH, f'Match #{match["match"]}')
        teams = []
        team = self.get_team_info(match['red1'])
        match_file_prefix = self.match_video_file_prefix('red', team['number'], match['match'])
        teams.append({'TeamName': team['name'], 'TeamNumber': team['number'], 'Alliance': 'Red', 'GameVideo': {'Location': f'{match_file_prefix}.mp4', 'VideoManifest': f'{match_file_prefix}.yml'}})
        team = self.get_team_info(match['red2'])
        match_file_prefix = self.match_video_file_prefix('red', team['number'], match['match'])
        teams.append({'TeamName': team['name'], 'TeamNumber': team['number'], 'Alliance': 'Red', 'GameVideo': {'Location': f'{match_file_prefix}.mp4', 'VideoManifest': f'{match_file_prefix}.yml'}})
        team = self.get_team_info(match['blue1'])
        match_file_prefix = self.match_video_file_prefix('blue', team['number'], match['match'])
        teams.append({'TeamName': team['name'], 'TeamNumber': team['number'], 'Alliance': 'Blue', 'GameVideo': {'Location': f'{match_file_prefix}.mp4', 'VideoManifest': f'{match_file_prefix}.yml'}})
        team = self.get_team_info(match['blue2'])
        match_file_prefix = self.match_video_file_prefix('blue', team['number'], match['match'])
        teams.append({'TeamName': team['name'], 'TeamNumber': team['number'], 'Alliance': 'Blue', 'GameVideo': {'Location': f'{match_file_prefix}.mp4', 'VideoManifest': f'{match_file_prefix}.yml'}})
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
            button = QtWidgets.QPushButton('-')
            self.matchstable.setCellWidget(row_no, 1, button)
            button.clicked.connect(self.button_click)

            team = self.get_team_info(match['red2'])
            item = QtWidgets.QTableWidgetItem(f"{team['number']} : {team['name']}")
            item.setFlags(item.flags() ^ QtCore.Qt.ItemIsEditable)
            item.setForeground(QtGui.QBrush(QtGui.QColor(QtCore.Qt.red)))
            self.matchstable.setItem(row_no, 2, item)
            button = QtWidgets.QPushButton('-')
            self.matchstable.setCellWidget(row_no, 3, button)
            button.clicked.connect(self.button_click)

            item = QtWidgets.QTableWidgetItem("-")
            item.setFlags(item.flags() ^ QtCore.Qt.ItemIsEditable)
            item.setForeground(QtGui.QBrush(QtGui.QColor(QtCore.Qt.red)))
            self.matchstable.setItem(row_no, 4, item)

            team = self.get_team_info(match['blue1'])
            item = QtWidgets.QTableWidgetItem(f"{team['number']} : {team['name']}")
            item.setFlags(item.flags() ^ QtCore.Qt.ItemIsEditable)
            item.setForeground(QtGui.QBrush(QtGui.QColor(QtCore.Qt.blue)))
            self.matchstable.setItem(row_no, 5, item)
            button = QtWidgets.QPushButton('-')
            self.matchstable.setCellWidget(row_no, 6, button)
            button.clicked.connect(self.button_click)

            team = self.get_team_info(match['blue2'])
            item = QtWidgets.QTableWidgetItem(f"{team['number']} : {team['name']}")
            item.setFlags(item.flags() ^ QtCore.Qt.ItemIsEditable)
            item.setForeground(QtGui.QBrush(QtGui.QColor(QtCore.Qt.blue)))
            self.matchstable.setItem(row_no, 7, item)
            button = QtWidgets.QPushButton('-')
            self.matchstable.setCellWidget(row_no, 8, button)
            button.clicked.connect(self.button_click)

            item = QtWidgets.QTableWidgetItem("-")
            item.setFlags(item.flags() ^ QtCore.Qt.ItemIsEditable)
            item.setForeground(QtGui.QBrush(QtGui.QColor(QtCore.Qt.blue)))
            self.matchstable.setItem(row_no, 9, item)

            row_no += 1

    def update_ui(self):
        """Check folder structure and updates the user interface"""
        if self.root_folder is not None:
            upload_folder = os.path.join(self.root_folder, self.FOLDER_TEAM)
            row_no = 0
            for match in self.quals:
                status, red1_score = self.video_status(upload_folder, match['match'], match['red1'], 'Red', row_no, 0)
                status, red2_score = self.video_status(upload_folder, match['match'], match['red2'], 'Red', row_no, 2)
                status, blue1_score = self.video_status(upload_folder, match['match'], match['blue1'], 'Blue', row_no, 5)
                status, blue2_score = self.video_status(upload_folder, match['match'], match['blue2'], 'Blue', row_no, 7)
                if red1_score and red2_score:
                    item = self.matchstable.item(row_no, 4)
                    item.setText(str(red1_score + red2_score))
                if blue1_score and blue2_score:
                    item = self.matchstable.item(row_no, 9)
                    item.setText(str(blue1_score + blue2_score))
                row_no += 1

    def video_status(self, upload_folder, match_number, team_number, alliance, table_row_no, table_column_no):
        team = self.get_team_info(team_number)
        team_folder, team_match_folder = self.match_upload_folder(upload_folder, team["number"], team["name"], match_number, alliance)
        upload_video = None
        with os.scandir(team_match_folder) as it:
            video_files = [entry for entry in it if entry.is_file() and entry.name.lower().endswith('.mp4')]
            if len(video_files) == 1:
                upload_video = os.path.normpath(video_files[0].path)
        match_folder = os.path.join(self.root_folder, self.FOLDER_MATCH, f'Match #{match_number}')
        match_file_prefix = self.match_video_file_prefix(alliance, team_number, match_number)
        match_video_filename = os.path.join(match_folder, f'{match_file_prefix}.mp4')
        video_manifest_filename = os.path.join(match_folder, f'{match_file_prefix}.yml')
        score = None
        textfield = self.matchstable.item(table_row_no, table_column_no)
        button = self.matchstable.cellWidget(table_row_no, table_column_no + 1)
        button.setProperty('team_number', team_number)
        button.setProperty('team_name', team["name"])
        button.setProperty('match_number', match_number)
        button.setProperty('match_video_filename', os.path.normpath(match_video_filename))
        button.setProperty('upload_video', upload_video)
        button.setProperty('team_folder', os.path.normpath(team_folder))
        if os.path.exists(video_manifest_filename):
            with open(video_manifest_filename) as file:
                video_manifest = yaml.load(file, Loader=yaml.SafeLoader)
                score = 0
                for item in video_manifest['GameEvents']:
                    score += item['Point']
                status = self.STATUS_REVIEWED
                textfield.setBackgroundColor(QtGui.QColor(QtCore.Qt.green))
        elif os.path.exists(match_video_filename):
            status = self.STATUS_COPIED
            textfield.setBackgroundColor(QtGui.QColor(QtCore.Qt.yellow))
        elif upload_video:
            status = self.STATUS_UPLOADED
            textfield.setBackgroundColor(QtGui.QColor(QtCore.Qt.gray))
        else:
            status = self.STATUS_NO_VIDEO
            textfield.setBackgroundColor(QtGui.QColor(QtCore.Qt.white))
        button.setText(status)
        return status, score

    STATUS_NO_VIDEO = 'No Video'
    STATUS_UPLOADED = 'Uploaded'
    STATUS_COPIED = 'Copied'
    STATUS_REVIEWED = 'Reviewed'

    def button_click(self):
        status = self.sender().text()
        if status == self.STATUS_REVIEWED:
            self.message_box(f'Game video of team #{self.sender().property("team_number")} {self.sender().property("team_name")} for match #{self.sender().property("match_number")} has been reviewed!')
        elif status == self.STATUS_COPIED:
            self.message_box(f'Please ask referees to review game video "{self.sender().property("match_video_filename")}" for team #{self.sender().property("team_number")} {self.sender().property("team_name")} and match #{self.sender().property("match_number")}')
        elif status == self.STATUS_UPLOADED:
            shutil.copy2(self.sender().property("upload_video"), self.sender().property("match_video_filename"))
            self.update_ui()
        elif status == self.STATUS_NO_VIDEO:
            self.message_box(f'Please share the folder "{self.sender().property("team_folder")}" to team #{self.sender().property("team_number")} {self.sender().property("team_name")} and ask them to upload game video for match #{self.sender().property("match_number")}')

    def message_box(self, msg):
        msgBox = QtWidgets.QMessageBox()
        msgBox.setText(msg)
        msgBox.exec_()


def main():
    """Entry point
    """
    app = QtWidgets.QApplication(sys.argv)
    db_file = None
    root_folder = None
    if len(sys.argv) > 1:
        filename = sys.argv[1]
        if path.isfile(filename):
            db_file = filename
        else:
            print(f'ERROR : DB file passed in [{filename}] not exists')
        if len(sys.argv) > 2:
            filename = sys.argv[2]
            if path.isdir(filename):
                root_folder = os.path.realpath(filename)
            else:
                print(f'ERROR : Root folder passed in [{filename}] not exists')
    player = EventPlanner(db_file=db_file, root_folder=root_folder)
    player.show()
    player.resize(1080, 720)
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
