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



class MatchVideoProcessor(QtWidgets.QMainWindow):

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

        if media_file is not None:
            self.open_media_file(media_file)

        self.is_paused = False

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

        self.htablebox = QtWidgets.QHBoxLayout()

        self.eventstabs = QtWidgets.QTabWidget()

        self.gamestart_tab = QtWidgets.QVBoxLayout()
        self.gamestart_rb = QtWidgets.QRadioButton("Game Start")
        self.gamestart_tab.addWidget(self.gamestart_rb)
        tab_widget = QtWidgets.QWidget()
        tab_widget.setLayout(self.gamestart_tab)
        self.eventstabs.addTab(tab_widget, 'Game Start')

        self.autonomous_tab = QtWidgets.QVBoxLayout()
        self.autonomous_tab.addWidget(QtWidgets.QRadioButton("Power Shot Target Knocked"))
        self.autonomous_tab.addWidget(QtWidgets.QRadioButton("Wobble Goal Delivered to Target Zone"))
        self.autonomous_tab.addWidget(QtWidgets.QRadioButton("Launched Rings into Low Goal"))
        self.autonomous_tab.addWidget(QtWidgets.QRadioButton("Launched Rings into Medium Goal"))
        self.autonomous_tab.addWidget(QtWidgets.QRadioButton("Launched Rings into High Goal"))
        self.autonomous_tab.addWidget(QtWidgets.QRadioButton("Robot Parked"))
        tab_widget = QtWidgets.QWidget()
        tab_widget.setLayout(self.autonomous_tab)
        self.eventstabs.addTab(tab_widget, 'Autonomous')

        self.teleop_tab = QtWidgets.QVBoxLayout()
        self.teleop_tab.addWidget(QtWidgets.QRadioButton("Launched Rings into Low Goal"))
        self.teleop_tab.addWidget(QtWidgets.QRadioButton("Launched Rings into Medium Goal"))
        self.teleop_tab.addWidget(QtWidgets.QRadioButton("Launched Rings into High Goal"))
        tab_widget = QtWidgets.QWidget()
        tab_widget.setLayout(self.teleop_tab)
        self.eventstabs.addTab(tab_widget, 'Teleop')

        self.endgame_tab = QtWidgets.QVBoxLayout()
        self.endgame_tab.addWidget(QtWidgets.QRadioButton("Power Shot Target Knocked"))
        self.endgame_tab.addWidget(QtWidgets.QRadioButton("Wobble Goal Delivered to Start Line"))
        self.endgame_tab.addWidget(QtWidgets.QRadioButton("Wobble Goal Delivered to Drop Zone"))
        self.endgame_tab.addWidget(QtWidgets.QRadioButton("Launched Rings into Low Goal"))
        self.endgame_tab.addWidget(QtWidgets.QRadioButton("Launched Rings into Medium Goal"))
        self.endgame_tab.addWidget(QtWidgets.QRadioButton("Launched Rings into High Goal"))
        self.endgame_tab.addWidget(QtWidgets.QRadioButton("Rings Supported by Wobble Goal"))
        tab_widget = QtWidgets.QWidget()
        tab_widget.setLayout(self.endgame_tab)
        self.eventstabs.addTab(tab_widget, 'End Game')

        self.penalty_tab = QtWidgets.QVBoxLayout()
        self.penalty_tab.addWidget(QtWidgets.QRadioButton("Minor Penalty"))
        self.penalty_tab.addWidget(QtWidgets.QRadioButton("Major Penalty"))
        tab_widget = QtWidgets.QWidget()
        tab_widget.setLayout(self.penalty_tab)
        self.eventstabs.addTab(tab_widget, 'Penalty')

        self.htablebox.addWidget(self.eventstabs, stretch=6)
        self.eventstable = QtWidgets.QTableWidget(2, 2)
        self.eventstable.setHorizontalHeaderLabels(['Event', 'Points'])
        self.eventstable.setVerticalHeaderLabels(['--:--', 'Total'])
        self.eventstable.setItem(1, 1, QtWidgets.QTableWidgetItem('0'))
        header = self.eventstable.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
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

    def add_event(self):
        """ Add the event
        """
        seconds = 12
        event = 'Game Start'
        point = 10
        target_row_no = None
        for row_no in range (self.eventstable.rowCount()):
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
                    target_row_no = row_no
                    self.eventstable.insertRow(target_row_no)
            else:
                # target row already found, pass
                pass
        if target_row_no is None:
            # insert the row to the end
            target_row_no = self.eventstable.rowCount() - 2
            self.eventstable.insertRow(target_row_no)
        # update target row
        self.eventstable.setVerticalHeaderItem(target_row_no, QtWidgets.QTableWidgetItem(seconds_to_mmss(seconds)))
        self.eventstable.setItem(target_row_no, 0, QtWidgets.QTableWidgetItem(event))
        self.eventstable.setItem(target_row_no, 1, QtWidgets.QTableWidgetItem(str(point)))

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

        # No need to call this function if nothing is played
        if not self.mediaplayer.is_playing():
            self.timer.stop()

            # After the video finished, the play button stills shows "Pause",
            # which is not the desired behavior of a media player.
            # This fixes that "bug".
            if not self.is_paused:
                self.reset()

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
