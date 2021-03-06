# Tutorial for Score Keeper #
## Setup ##
- Setup the shared folder as desribed in this doc : [ShareFolder](./ShareFolder.md)
- Install official FTC Score keeper software at https://github.com/FIRST-Tech-Challenge/scorekeeper
- Download latest release of VirtualGameEvent package (click Releases link on left panel)
- Unzip VirtualGameEvent-vX.X-YYYY-MM-DD.zip, and start Event Planner by run event-planner.exe
## Generate match schedule and folder structure ##
- Setup matches in FTC score keeper
- In Event Planner, open the event database of FTC score keeper (usually at \path\to\scorekeeper\db\ folder with an extension .db) 
- Then click "Generate Folder Skeleton" button, it will you to choose a folder, please choose a folder in the shared folder
- Following sub folders will generated : 
  - Team Uploads : A folder for individual teams to upload their game videos, organized by team by match
  - Game Matches : Stored match manifest and video manifest files by match, and referee should run Match Video Processor to review game
  - Match Video Published : Store the generated match videos for publish
- Share the sub folders of "Team Uploads" to each of individual team
  - It's better ensure a team cannot access other team's folder to avoid mistake, frustration and privacy concerns.
## Monitoring the progress ##
- When a team uploaded the video of game, the corresponding item on EventPlanner will turn to color gray
- Please verify the video uploaded is legitmate, then click the button to copy the video file to "Game Matches" folder automatically, the item will turn to color yellow
- Please notify the referee to review the game video, once they are done and generate the video manifest file, the item will turn to color green
- If both team of the alliance video reviewed, a score will show up
- Once both alliances reviewed and score shows up, please notify the video publisher to generate the game video.
## Import final score to FTC score software ##
- After the match has been reviewed by referee, the button on FTC column will be enabled and show as "ScoreKeeper"
- Click "ScoreKeeper" button will save the score of the match back to FTC Score Keeper as a "Scorekeeper Edit" of that match's history
- Close FTC Scorekeeper if it's open
- Reopen FTC Scorekeeper
- Login
- Go to "Match Control"
- Click "Enter Scores" or "Edit" for the corresponding match
- Click "View History" and select generated record
- Click "Copy to Editor"
- Review and adjust before "Commit"
### KNOWN ISSUE ###
- FTC Scorekeeper is design to for traditional live event, and treat the mid goal points differently than remote event, please manually review and adjust the mid goal points in FTC score keeper. 


