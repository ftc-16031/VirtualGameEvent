## Summary ##

Most features of VirtualGameEvent rely on file system, when a group of volunteers to run the virtual event, it's crucial that the team can work on shared folder. It's not a feature of VirtualGameEvent but an essential part of the whole solution. There are many ways to share a folder within the team, following in this doc we summary couple of solutions. 

## Share folder with OneDrive ##
 
### Advantage ###
- Free (limit to 5GB)
- $2 for 100GB
- Official support Windows
- OneDrive software can sync folders that are shared with you (Google Drive cannot)

### Suggested Steps ###
#### Owner of shared folder ####
- Create a folder and share with the team (score keeper, referee, video publisher etc.)
#### Team members ####
- Using the web interface for OneDrive, find the shared folder under the "Shared" tab
- Right click and select "Add to my OneDrive"
- Open file explorer on your PC and find the shared folder in OneDrive (it should have a cloud and person icon in the status column)
- Right click and select "Always keep on this device" (the status icon should change to syncing)
- Then use EventPlanner to create folder structures in the local folder

## Share folder with Google Drive ##
 
### Advantage ###
- Free (limit to 15GB per account)
- Official support Windows and MacOS
- Multiple accounts supported

### Disadvantage ###
- Google Backup&Sync software can only sync My Drive folder, not "Shared With me" folder
### Suggested Steps ###
- Create a dedicate Google account for the scrimmage (Free)
- Share the account and password with the team (score keeper, referee, video publisher etc.)
- Install Google Backup&Sync on your PC
- Add New Account
- **Do NOT** "backup" or "connect" any local folder to this Google account
- **Do NOT** upload photos and videos to this Google account
- Sync the Google Drive to a local folder
- Then use EventPlanner to create folder structures in the local folder

## Share folder with dropbox ##
## Share folder with AWS S3 ##
