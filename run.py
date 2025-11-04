import argparse
import os
import sys
import subprocess

from config import load_config
from scripts.logging_controller import get_logger

arg_desc = "AppAgent - deployment phase"
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, description=arg_desc)
parser.add_argument("--app")
parser.add_argument("--root_dir", default="./")
args = vars(parser.parse_args())

app = args["app"]
root_dir = args["root_dir"]

try:
    logger = get_logger()
except Exception as e:
    print(f"ERROR: Failed to load logger configuration: {e}")
    sys.exit(1)

try:
    configs = load_config()
except Exception as e:
    logger.error(f"ERROR: Failed to load configuration: {e}")
    sys.exit(1)

def temp_speak(text: str):
    try:
        if sys.platform == "darwin":
            voice = configs.get("VOICE_TYPE", "Veena")
            rate = configs.get("VOICE_SPEED", 170)
            cmd = ["say"]
            if voice:
                cmd += ["-v", voice]
            if rate:
                cmd += ["-r", rate]
            cmd += [text]
            subprocess.run(cmd, check=False)
    except Exception:
        logger.error(f"ERROR: In speaking as exception {e}")
        pass

logger.show("Welcome to mobile agent of L&T Finace")
if configs.get("ENABLE_VOICE", False):
    temp_speak("Welcome to mobile agent of L&T Finace")
    

# logger.show("Welcome to the deployment phase of AppAgent!\nBefore giving me the task, you should first tell me "
#                  "the name of the app you want me to operate and what documentation base you want me to use. I will "
#                  "try my best to complete the task without your intervention. First, please enter the main interface "
#                  "of the app on your phone and provide the following information.")

if not app:
    # ToDo: Saurabh. Change later to different apps too.
    # logger.show("What is the name of the target app?")
    # app = input()
    app = "planet"
    app = app.replace(" ", "")

os.system(f"python scripts/task_executor.py --app {app} --root_dir {root_dir}")
