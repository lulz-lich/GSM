          _____                    _____                    _____          
         /\    \                  /\    \                  /\    \         
        /::\    \                /::\    \                /::\____\        
       /::::\    \              /::::\    \              /::::|   |        
      /::::::\    \            /::::::\    \            /:::::|   |        
     /:::/\:::\    \          /:::/\:::\    \          /::::::|   |        
    /:::/  \:::\    \        /:::/__\:::\    \        /:::/|::|   |        
   /:::/    \:::\    \       \:::\   \:::\    \      /:::/ |::|   |        
  /:::/    / \:::\    \    ___\:::\   \:::\    \    /:::/  |::|___|______  
 /:::/    /   \:::\ ___\  /\   \:::\   \:::\    \  /:::/   |::::::::\    \ 
/:::/____/  ___\:::|    |/::\   \:::\   \:::\____\/:::/    |:::::::::\____\
\:::\    \ /\  /:::|____|\:::\   \:::\   \::/    /\::/    / ~~~~~/:::/    /
 \:::\    /::\ \::/    /  \:::\   \:::\   \/____/  \/____/      /:::/    / 
  \:::\   \:::\ \/____/    \:::\   \:::\    \                  /:::/    /  
   \:::\   \:::\____\       \:::\   \:::\____\                /:::/    /   
    \:::\  /:::/    /        \:::\  /:::/    /               /:::/    /    
     \:::\/:::/    /          \:::\/:::/    /               /:::/    /     
      \::::::/    /            \::::::/    /               /:::/    /      
       \::::/    /              \::::/    /               /:::/    /       
        \::/____/                \::/    /                \::/    /        
                                  \/____/                  \/____/         
                                                                           
Game Save Manager for Linux and Windows.

GSM creates versioned backups of game saves, uploads them to the cloud, synchronizes the backup library between machines, and restores saves when needed.

It is designed to work safely across Linux and Windows without one side corrupting or deleting the other.

---

## Main Features

- Automatic save detection with Ludusavi
- Manual backup for unsupported games
- Cloud upload with Rclone
- Versioned backups per game
- SHA256 integrity files
- Backup retention per game
- Sync backup library from cloud
- Restore latest backup
- Restore all backups
- Restore the latest backup of a specific game
- Linux GUI
- Linux TUI
- Windows GUI
- Linux AppImage support
- Windows single-file EXE build

---

## Important Safety Rule

GSM uses:

```text
rclone copy
