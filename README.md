Currently not fully tested. Could contain bugs. Proceed with caution. Requirements.txt file is for NVIDIA gpus only and could not work at all on other devices. Needs more testing

-Free space needed 32,5 GB for all models and extra stuff. Could probably just download without git lfs. (Large file support) and manually download Pruned if less than 4gb ram or Full 5.5gb version if more than 8gb vram. NSWF safety filter disabled by default and should work just fine without it by adding nsfw, nude, naked in negative prompt if needed. 

# 1:

Open Terminal

Commands are for Arch, Manjaro etc. For other distros slightly different.

Optional, but highly recommended: "sudo pacman -Syu" to update all other packages

Install git: "sudo pacman -S git"

Verify installation with: "git --version" All good if got output "git version 2.35.1" or similar

Install pip: "sudo pacman -S python-pip"

Then: "pip install -r requirements.txt"

# 2:

Example uses Protogen_x3.4_Official_Release but you can use any other model. Recommended Vram for pruned version is 4gb+ 1.7gb model works fine on NVIDIA GeForce GTX 960 4gb

https://huggingface.co/darkstorm2150/Protogen_x3.4_Official_Release/tree/main Has more details on how to install.

# Easiest way:

Change conf.json "model_index_to_use" to 1. First slot is 0, second 1, third 2 etc

Automatically installs protogen x3.4.

# Better for more control but does take a long time to download all:

Create new folder "models" in same directory as main.py and conf.json.

Open terminal and make sure its in .../models/ (use ls and cs /folder/ to navigate)

Make sure you have git-lfs installed (https://git-lfs.com)

git lfs install

git clone https://huggingface.co/darkstorm2150/Protogen_x3.4_Official_Release

After finishing downloading

Change conf.json "model_location" to "./models/Protogen_x3.4_Official_Release" and make sure downloaded folder looks same as https://huggingface.co/darkstorm2150/Protogen_x3.4_Official_Release/tree/main. If not in right place you can change model location accordingly Example "C:/Path/to/model" or move it, breaks git stuff but should work just fine.

# 3:

Change conf.json Username and telegram bot token (can be get from telegram Bot Father https://t.me/BotFather recommended to Disable /setjoingroups, add some description and commands list, but not needed works without changing anything only needs bot token and bot username in conf.json). Admins can be added for /g4, /g9 and /set_default_n_prompt command

# 4:

Then everything should be good to go.

Run in terminal "python main.py"

Closing Terminal shutdowns the bot

# Troubleshooting:

Most common problems: Verify all python pip modules in requirements.txt are installed. (easiest to check with any code editor)
