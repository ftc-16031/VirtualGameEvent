"""
Match Video Processor to playback match video and generate "video manifest" file
  with VLC python bindings using PyQt5.

Author: FTC team #16031 Parabellum
Date: 25 Jan 2021
"""

import platform
import os
import sys
import re
import yaml
from os import path

from PySide2 import QtWidgets, QtGui, QtCore
import vlc


def ms_to_mmss(ms):
    return seconds_to_mmss(int(ms/1000))


def seconds_to_mmss(time):
    minutes, seconds = divmod(time, 60)
    return f'{minutes:02}:{seconds:02}'


offset_pattern = re.compile(r'^([0-9]+):([0-9]+)$')


def mmss_to_seconds(mmss):
    if type(mmss) == str:
        offset_parts = offset_pattern.match(mmss)
        assert offset_parts is not None, 'Game event timestamp must be in "MM:SS" format'
        return int(offset_parts.group(1)) * 60 + int(offset_parts.group(2))
    else:
        print(f'ERROR : cannot process mmss [{mmss}]')
        return mmss


class InvalidEventException(Exception):
    def __init__(self, message):
        self.message = message


class MatchVideoProcessor(QtWidgets.QMainWindow):

    game_start_offset = None

    def __init__(self, media_file=None, master=None):
        QtWidgets.QMainWindow.__init__(self, master)
        self.setWindowTitle("Match Video Processor")
        self.showMaximized()

        # Create a basic vlc instance
        self.instance = vlc.Instance()

        self.media = None

        # Create an empty vlc media player
        self.mediaplayer = self.instance.media_player_new()

        self.create_ui()

        self.is_paused = False

        if media_file is not None:
            self.open_media_file(media_file)

    def ring_goal_event_widgets(self):
        radiobutton = QtWidgets.QRadioButton("Launched Rings into Goals")
        ring_goals = QtWidgets.QHBoxLayout()
        high_goal = QtWidgets.QSpinBox()
        high_goal.setRange(0, 3)
        high_goal.setValue(0)
        ring_goals.addStretch(1)
        ring_goals.addWidget(QtWidgets.QLabel('High: '))
        ring_goals.addWidget(high_goal)
        ring_goals.addStretch(1)
        medium_goal = QtWidgets.QSpinBox()
        medium_goal.setRange(0, 3)
        medium_goal.setValue(0)
        ring_goals.addWidget(QtWidgets.QLabel('Medium: '))
        ring_goals.addWidget(medium_goal)
        ring_goals.addStretch(1)
        low_goal = QtWidgets.QSpinBox()
        low_goal.setRange(0, 3)
        low_goal.setValue(0)
        ring_goals.addWidget(QtWidgets.QLabel('Low: '))
        ring_goals.addWidget(low_goal)
        ring_goals.addStretch(1)
        associated_widgets = {'high': high_goal, 'medium': medium_goal, 'low': low_goal}
        return ring_goals, radiobutton, associated_widgets

    def create_ui(self):
        """Set up the user interface, signals & slots
        """
        self.widget = QtWidgets.QWidget(self)
        self.setCentralWidget(self.widget)

        # In this widget, the video will be drawn
        if platform.system() == "Darwin": # for MacOS
            self.videoframe = QtWidgets.QMacCocoaViewContainer(0)
        else:
            self.videoframe = QtWidgets.QFrame()

        self.palette = self.videoframe.palette()
        self.palette.setColor(QtGui.QPalette.Window, QtGui.QColor(0, 0, 0))
        self.videoframe.setPalette(self.palette)
        self.videoframe.setAutoFillBackground(True)

        self.positionslider = QtWidgets.QSlider(QtCore.Qt.Horizontal, self)
        self.positionslider.setToolTip("Position")
        self.positionslider.setMaximum(1000)
        self.positionslider.sliderMoved.connect(self.set_position)
        self.positionslider.sliderPressed.connect(self.set_position)

        self.hbuttonbox = QtWidgets.QHBoxLayout()
        self.playbutton = QtWidgets.QPushButton("Play")
        self.hbuttonbox.addWidget(self.playbutton)
        self.playbutton.clicked.connect(self.play_pause)
        self.resetbutton = QtWidgets.QPushButton("Reset")
        self.hbuttonbox.addWidget(self.resetbutton)
        self.resetbutton.clicked.connect(self.reset)

        self.hbuttonbox.addStretch(1)
        self.progress = QtWidgets.QLabel("--:--")
        self.hbuttonbox.addWidget(self.progress)
        self.addeventbutton = QtWidgets.QPushButton("Add Event")
        self.hbuttonbox.addWidget(self.addeventbutton)
        self.addeventbutton.clicked.connect(self.add_event)
        self.hbuttonbox.addStretch(1)
        self.savebutton = QtWidgets.QPushButton("Save Video Manifest")
        self.hbuttonbox.addWidget(self.savebutton)
        self.savebutton.clicked.connect(self.save_manifest)

        self.htablebox = QtWidgets.QHBoxLayout()

        self.eventstabs = QtWidgets.QTabWidget()

        self.events=[]
        self.events.append([])
        tab = QtWidgets.QVBoxLayout()
        radiobutton = QtWidgets.QRadioButton("Game Start")
        tab.addWidget(radiobutton)
        # automatically select the game start button
        radiobutton.setChecked(True)
        self.events[0].append({'radio_button': radiobutton, 'handler': self.game_start_event, 'associated_widgets': {}})
        tab_widget = QtWidgets.QWidget()
        tab_widget.setLayout(tab)
        self.eventstabs.addTab(tab_widget, 'Game Start')

        self.events.append([])
        tab = QtWidgets.QVBoxLayout()
        # wobble goal
        radiobutton = QtWidgets.QRadioButton("Wobble Goal Delivered to Target Zone")
        tab.addWidget(radiobutton)
        self.events[1].append({'radio_button': radiobutton, 'handler': self.wobblegoal_target_event, 'associated_widgets': {}})
        # parking
        radiobutton = QtWidgets.QRadioButton("Robot Parked")
        tab.addWidget(radiobutton)
        self.events[1].append({'radio_button': radiobutton, 'handler': self.robot_park_event, 'associated_widgets': {}})
        # ring goal
        ring_goals, radiobutton, associated_widgets = self.ring_goal_event_widgets()
        tab.addWidget(radiobutton)
        tab.addLayout(ring_goals)
        self.events[1].append({'radio_button': radiobutton, 'handler': self.ring_goal_auto_event, 'associated_widgets': associated_widgets})
        # power shot
        radiobutton = QtWidgets.QRadioButton("Power Shot Target Knocked")
        tab.addWidget(radiobutton)
        self.events[1].append({'radio_button': radiobutton, 'handler': self.powershot_event, 'associated_widgets': {}})
        # tab
        tab_widget = QtWidgets.QWidget()
        tab_widget.setLayout(tab)
        self.eventstabs.addTab(tab_widget, 'Autonomous')

        self.events.append([])
        tab = QtWidgets.QVBoxLayout()
        ring_goals, radiobutton, associated_widgets = self.ring_goal_event_widgets()
        tab.addWidget(radiobutton)
        tab.addLayout(ring_goals)
        self.events[2].append({'radio_button': radiobutton, 'handler': self.ring_goal_teleop_event, 'associated_widgets': associated_widgets})
        tab_widget = QtWidgets.QWidget()
        tab_widget.setLayout(tab)
        self.eventstabs.addTab(tab_widget, 'Teleop')

        self.events.append([])
        tab = QtWidgets.QVBoxLayout()
        # wobble goal to start line
        radiobutton = QtWidgets.QRadioButton("Wobble Goal Delivered to Start Line")
        tab.addWidget(radiobutton)
        self.events[3].append({'radio_button': radiobutton, 'handler': self.wobblegoal_startline_event, 'associated_widgets': {}})
        # wobble goal to drop zone
        radiobutton = QtWidgets.QRadioButton("Wobble Goal Delivered to Drop Zone")
        tab.addWidget(radiobutton)
        self.events[3].append({'radio_button': radiobutton, 'handler': self.wobblegoal_dropzone_event, 'associated_widgets': {}})
        # ring goal
        ring_goals, radiobutton, associated_widgets = self.ring_goal_event_widgets()
        tab.addWidget(radiobutton)
        tab.addLayout(ring_goals)
        self.events[3].append({'radio_button': radiobutton, 'handler': self.ring_goal_teleop_event, 'associated_widgets': associated_widgets})
        # power shot
        radiobutton = QtWidgets.QRadioButton("Power Shot Target Knocked")
        tab.addWidget(radiobutton)
        self.events[3].append({'radio_button': radiobutton, 'handler': self.powershot_event, 'associated_widgets': {}})
        # tab
        tab_widget = QtWidgets.QWidget()
        tab_widget.setLayout(tab)
        self.eventstabs.addTab(tab_widget, 'End Game')

        self.events.append([])
        tab = QtWidgets.QVBoxLayout()
        penalty_layout = QtWidgets.QHBoxLayout()
        radiobutton = QtWidgets.QRadioButton("Minor Penalty")
        penalty_layout.addWidget(radiobutton)
        ring_goals.addStretch(1)
        reason_edit = QtWidgets.QLineEdit()
        penalty_layout.addWidget(reason_edit)
        ring_goals.addStretch(1)
        tab.addLayout(penalty_layout)
        self.events[4].append({'radio_button': radiobutton, 'handler': self.minor_penalty_event, 'associated_widgets': {'reason': reason_edit}})
        penalty_layout = QtWidgets.QHBoxLayout()
        radiobutton = QtWidgets.QRadioButton("Major Penalty")
        penalty_layout.addWidget(radiobutton)
        ring_goals.addStretch(1)
        reason_edit = QtWidgets.QLineEdit()
        penalty_layout.addWidget(reason_edit)
        ring_goals.addStretch(1)
        tab.addLayout(penalty_layout)
        self.events[4].append({'radio_button': radiobutton, 'handler': self.major_penalty_event, 'associated_widgets': {'reason': reason_edit}})
        tab_widget = QtWidgets.QWidget()
        tab_widget.setLayout(tab)
        self.eventstabs.addTab(tab_widget, 'Penalty')

        self.htablebox.addWidget(self.eventstabs, stretch=6)
        self.eventstable = QtWidgets.QTableWidget(2, 3)
        self.eventstable.setHorizontalHeaderLabels(['Event', 'Points', ''])
        header = self.eventstable.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        self.htablebox.addWidget(self.eventstable, stretch=4)

        self.vboxlayout = QtWidgets.QVBoxLayout()
        self.vboxlayout.addWidget(self.videoframe, stretch=10)
        self.vboxlayout.addWidget(self.positionslider)
        self.vboxlayout.addLayout(self.hbuttonbox)
        self.vboxlayout.addLayout(self.htablebox, stretch=7)

        self.widget.setLayout(self.vboxlayout)

        menu_bar = self.menuBar()

        # File menu
        file_menu = menu_bar.addMenu("File")

        # Add actions to file menu
        open_action = QtWidgets.QAction("Load Video", self)
        close_action = QtWidgets.QAction("Close App", self)
        file_menu.addAction(open_action)
        file_menu.addAction(close_action)

        open_action.triggered.connect(self.open_file)
        close_action.triggered.connect(sys.exit)

        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.update_ui)

        self.reset()

    def play_pause(self):
        """Toggle play/pause status
        """
        if self.mediaplayer.is_playing():
            self.mediaplayer.pause()
            self.playbutton.setText("Play")
            self.is_paused = True
            self.timer.stop()
        else:
            if self.mediaplayer.play() == -1:
                self.open_file()
                return

            self.mediaplayer.play()
            self.playbutton.setText("Pause")
            self.timer.start()
            self.is_paused = False

    def reset(self):
        """Stop player
        """
        self.mediaplayer.stop()
        self.playbutton.setText("Play")
        self.progress.setText("--:--")
        for row_no in range (self.eventstable.rowCount()):
            self.eventstable.removeRow(0)
        self.eventstable.insertRow(0)
        self.eventstable.insertRow(0)
        self.eventstable.setVerticalHeaderLabels(['--:--', 'Total'])
        self.eventstable.setItem(1, 1, QtWidgets.QTableWidgetItem('0'))
        self.eventstabs.setTabEnabled(0, True)
        self.eventstabs.setTabEnabled(1, False)
        self.eventstabs.setTabEnabled(2, False)
        self.eventstabs.setTabEnabled(3, False)
        self.eventstabs.setTabEnabled(4, False)
        self.eventstabs.setCurrentIndex(0)
        self.game_start_offset = None
        self.savebutton.setEnabled(False)

    def save_manifest(self):
        pre, ext = os.path.splitext(self.media_filename)
        manifest_filename, _ = QtWidgets.QFileDialog.getSaveFileName(caption="Match Manifest File", dir=f'{pre}.yml')
        manifest = {'GameStartOffset': seconds_to_mmss(self.game_start_offset), 'GameEvents': []}
        for row_no in range(self.eventstable.rowCount()):
            row_name = self.eventstable.verticalHeaderItem(row_no).text()
            if row_name != 'Total':
                # ignore total row
                event_description = self.eventstable.item(row_no, 0).text()
                point = int(self.eventstable.item(row_no, 1).text())
                if event_description != 'Game Start':
                    # ignore game start row as well
                    event = {'Time': row_name, 'Description': event_description, 'Point': point}
                    manifest['GameEvents'].append(event)
        stream = open(manifest_filename, 'w')
        yaml.safe_dump(manifest, stream)
        return

    def game_start_event(self, radiobutton, timestamp, associated_widgets):
        self.game_start_offset = timestamp
        self.eventstabs.setTabEnabled(0, False)
        self.eventstabs.setTabEnabled(1, True)
        self.eventstabs.setTabEnabled(2, False)
        self.eventstabs.setTabEnabled(3, False)
        self.eventstabs.setTabEnabled(4, True)
        self.eventstabs.setCurrentIndex(1)
        self.savebutton.setEnabled(True)
        return radiobutton.text(), 0, timestamp

    def powershot_event(self, radiobutton, timestamp, associated_widgets):
        return radiobutton.text(), 15, timestamp

    def wobblegoal_target_event(self, radiobutton, timestamp, associated_widgets):
        return radiobutton.text(), 15, timestamp

    def wobblegoal_startline_event(self, radiobutton, timestamp, associated_widgets):
        return radiobutton.text(), 5, timestamp

    def wobblegoal_dropzone_event(self, radiobutton, timestamp, associated_widgets):
        return radiobutton.text(), 20, timestamp

    def ring_goal_event(self, radiobutton, timestamp, associated_widgets, points_schema):
        low_goal_point, medium_goal_point, high_goal_point = points_schema
        text = radiobutton.text() + ','
        total_points = 0
        if associated_widgets['high'].value() > 0:
            total_points += high_goal_point * associated_widgets['high'].value()
            text += f" high ({associated_widgets['high'].value()})"
        if associated_widgets['medium'].value() > 0:
            total_points += medium_goal_point * associated_widgets['medium'].value()
            text += f" medium ({associated_widgets['medium'].value()})"
        if associated_widgets['low'].value() > 0:
            total_points += low_goal_point * associated_widgets['low'].value()
            text += f" low ({associated_widgets['low'].value()})"
        if total_points == 0:
            raise InvalidEventException('Please specify number of rings launched into goals!')
        return text, total_points, timestamp

    def ring_goal_auto_event(self, radiobutton, timestamp, associated_widgets):
        points_schema = (3, 6, 12)
        return self.ring_goal_event(radiobutton, timestamp, associated_widgets, points_schema)

    def ring_goal_teleop_event(self, radiobutton, timestamp, associated_widgets):
        points_schema = (2, 4, 6)
        return self.ring_goal_event(radiobutton, timestamp, associated_widgets, points_schema)

    def robot_park_event(self, radiobutton, timestamp, associated_widgets):
        return radiobutton.text(), 5, timestamp

    def major_penalty_event(self, radiobutton, timestamp, associated_widgets):
        text = radiobutton.text()
        if len(associated_widgets['reason'].text()) > 0:
            text += f", {associated_widgets['reason'].text()}"
        else:
            raise InvalidEventException('Please specify a reason for the penalty!')
        return text, -30, timestamp

    def minor_penalty_event(self, radiobutton, timestamp, associated_widgets):
        text = radiobutton.text()
        if len(associated_widgets['reason'].text()) > 0:
            text += f", {associated_widgets['reason'].text()}"
        else:
            raise InvalidEventException('Please specify a reason for the penalty!')
        return text, -10, timestamp

    def add_event(self):
        """ Add the event
        """
        # check if there is a event selected
        current_tab = self.eventstabs.currentIndex()
        for event in self.events[current_tab]:
            if event['radio_button'].isChecked():
                timestamp = int(self.mediaplayer.get_time() / 1000)
                try:
                    event_text, point, seconds = event['handler'](event['radio_button'], timestamp, event['associated_widgets'])
                except InvalidEventException as ex:
                    msgBox = QtWidgets.QMessageBox()
                    msgBox.setText(ex.message)
                    msgBox.exec_()
                    return
                self.update_events_table(seconds, event_text, point)
                return
        msgBox = QtWidgets.QMessageBox()
        msgBox.setText("Please select an event to add !")
        msgBox.exec_()

    def update_events_table(self, seconds, event, point):
        target_row_no = None
        for row_no in range(self.eventstable.rowCount()):
            row_name = self.eventstable.verticalHeaderItem(row_no).text()
            if row_name == '--:--':
                # no event yet, update the initial row
                target_row_no = row_no
            elif row_name == 'Total':
                # update total row
                previous_total = int(self.eventstable.item(row_no, 1).text())
                self.eventstable.item(row_no, 1).setText(str(previous_total + point))
            elif target_row_no is None:
                # target row not found yet, compare the time and see if we need to insert
                row_time = mmss_to_seconds(row_name)
                if row_time > seconds:
                    target_row_no = row_no + 1
                    self.eventstable.insertRow(target_row_no)
            else:
                # target row already found, add +1 to all the row number for the delete button
                button = self.eventstable.cellWidget(row_no, 2)
                button.setProperty('row_no', button.property('row_no') + 1)
        if target_row_no is None:
            # insert the row to the end
            target_row_no = self.eventstable.rowCount() - 1
            self.eventstable.insertRow(target_row_no)
        # update target row
        self.eventstable.setVerticalHeaderItem(target_row_no, QtWidgets.QTableWidgetItem(seconds_to_mmss(seconds)))
        self.eventstable.setItem(target_row_no, 0, QtWidgets.QTableWidgetItem(event))
        self.eventstable.setItem(target_row_no, 1, QtWidgets.QTableWidgetItem(str(point)))
        if event != 'Game Start':
            # only add delete button for point events
            button = QtWidgets.QPushButton('X')
            button.setProperty('row_no', target_row_no)
            button.clicked.connect(self.delete_button_click)
            self.eventstable.setCellWidget(target_row_no, 2, button)

    def delete_button_click(self):
        delete_row_no = self.sender().property("row_no")
        self.eventstable.removeRow(delete_row_no)
        for row_no in range (delete_row_no, self.eventstable.rowCount()):
            button = self.eventstable.cellWidget(row_no, 2)
            if button:
                button.setProperty('row_no', button.property('row_no') - 1)

    def open_file(self):
        """Open a media file in a MediaPlayer
        """

        dialog_txt = "Choose Media File"
        filename = QtWidgets.QFileDialog.getOpenFileName(self, dialog_txt, os.path.expanduser('~'))
        if not filename:
            return

        # getOpenFileName returns a tuple, so use only the actual file name
        self.open_media_file(filename[0])

    def open_media_file(self, filename):

        self.media_filename = filename
        self.media = self.instance.media_new(filename)

        # Put the media in the media player
        self.mediaplayer.set_media(self.media)

        # Parse the metadata of the file
        self.media.parse()

        # Set the title of the track as window title
        self.setWindowTitle("Match Video Processor - " + self.media.get_meta(0))

        # The media player has to be 'connected' to the QFrame (otherwise the
        # video would be displayed in it's own window). This is platform
        # specific, so we must give the ID of the QFrame (or similar object) to
        # vlc. Different platforms have different functions for this
        if platform.system() == "Linux": # for Linux using the X Server
            self.mediaplayer.set_xwindow(int(self.videoframe.winId()))
        elif platform.system() == "Windows": # for Windows
            self.mediaplayer.set_hwnd(int(self.videoframe.winId()))
        elif platform.system() == "Darwin": # for MacOS
            self.mediaplayer.set_nsobject(int(self.videoframe.winId()))

        self.play_pause()

    def set_volume(self, volume):
        """Set the volume
        """
        self.mediaplayer.audio_set_volume(volume)

    def set_position(self):
        """Set the movie position according to the position slider.
        """

        # The vlc MediaPlayer needs a float value between 0 and 1, Qt uses
        # integer variables, so you need a factor; the higher the factor, the
        # more precise are the results (1000 should suffice).

        # Set the media position to where the slider was dragged
        self.timer.stop()
        pos = self.positionslider.value()
        self.mediaplayer.set_position(pos / 1000.0)
        self.timer.start()

    def update_ui(self):
        """Updates the user interface"""

        # Set the slider's position to its corresponding media position
        # Note that the setValue function only takes values of type int,
        # so we must first convert the corresponding media position.
        media_pos = int(self.mediaplayer.get_position() * 1000)
        self.positionslider.setValue(media_pos)
        self.progress.setText(f"{ms_to_mmss(self.mediaplayer.get_time())} / {ms_to_mmss(self.mediaplayer.get_length())}")

        # automatically switch the events tab status based on game start offset
        if self.game_start_offset is not None:
            seconds_from_game_start = int(self.mediaplayer.get_time()/1000) - self.game_start_offset
            if 0 <= seconds_from_game_start < 42:
                # enable the 'autonomous' tab
                self.eventstabs.setTabEnabled(1, True)
                # self.eventstabs.setCurrentIndex(1)
            if 0 <= seconds_from_game_start < 25:
                # disable the 'teleop' and 'end game' tab
                self.eventstabs.setTabEnabled(2, False)
                self.eventstabs.setTabEnabled(3, False)
            if 25 <= seconds_from_game_start < 130:
                # enable the 'teleop' tab
                self.eventstabs.setTabEnabled(2, True)
                if seconds_from_game_start == 35:
                    self.eventstabs.setCurrentIndex(2)
            if 30 <= seconds_from_game_start < 122:
                # disable the 'autonomous' and 'end game' tab
                self.eventstabs.setTabEnabled(1, False)
                self.eventstabs.setTabEnabled(3, False)
            if 122 <= seconds_from_game_start < 170:
                # enable the 'end game' tab
                self.eventstabs.setTabEnabled(3, True)
                if seconds_from_game_start == 130:
                    self.eventstabs.setCurrentIndex(3)
            if 125 <= seconds_from_game_start < 170:
                # disable the 'autonomous' and 'teleop' tab
                self.eventstabs.setTabEnabled(1, False)
                self.eventstabs.setTabEnabled(2, False)

        # No need to call this function if nothing is played
        if not self.mediaplayer.is_playing():
            self.timer.stop()


def main():
    """Entry point for our processor
    """
    app = QtWidgets.QApplication(sys.argv)
    media_file = None
    if len(sys.argv) > 1:
        filename = sys.argv[1]
        if path.isfile(filename):
            media_file = filename
        else:
            print(f'ERROR : Media file passed in [{filename}] not exists')
    player = MatchVideoProcessor(media_file=media_file)
    player.show()
    player.resize(640, 480)
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
