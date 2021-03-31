# Tutorial for Referee #
## Setup ##
- Setup the shared folder as desribed in this doc : [ShareFolder](./ShareFolder.md)
- Install VLC software (install from: https://www.videolan.org/vlc/index.html, support Windows, MacOS, and Linux)
- Download latest release of VirtualGameEvent package (click Releases link on left panel)
- Unzip VirtualGameEvent-vX.X-YYYY-MM-DD.zip, and start Match Video Processor by run match-video-processer.exe
## Review the game video ##
- When video file shows up in shared folder \Game Matches\Match #xx\ folder
- Using Match Video Processor to open the video file
- Play the video and when the game starts (usually at the computer voice "3, 2, 1, Music"), click "Add Event" with "Game Starts" event selected.
- Watch the video and when a game event (either scoring event, or penalty event) happens choose the corresponding event, input necessary information and click "Add Event"
- You can play, pause the video as well as jump to any position with the slide bar. 
- The events are organized in tabs by different stages of game ("Autonomous", "Teleop", "End Game"), and on different tabs you can only have corresponding scoring events for that stage.
- Event time, and points are automatically added. 
- You can delete an event by click "X" button
## Save Video Manifest file ##
- When game has been reviewed, click "Save Video Manifest" button to generate the corresponding video manifest file.
- When open the video file again, if the video manifest file (*.yml) with the same name exists, the previous game events will be automatically loaded together with the video

