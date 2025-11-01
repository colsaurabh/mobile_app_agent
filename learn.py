import argparse
import datetime
import os
import time

from scripts.print_controller import print_with_color

arg_desc = "AppAgent - exploration phase"
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, description=arg_desc)
parser.add_argument("--app")
parser.add_argument("--root_dir", default="./")
args = vars(parser.parse_args())

app = args["app"]
root_dir = args["root_dir"]


# ToDo: Saurabh. Change later to Autonomous & Human
print_with_color("Welcome to your L&T Finance agent", "yellow")
# print_with_color("Choose from the following modes:\n1. autonomous exploration\n2. human demonstration", "blue")
user_input = "1"
# while user_input != "1" and user_input != "2":
#     user_input = input()

if not app:
    # ToDo: Saurabh. Change later to different apps too.
    # print_with_color("What is the name of the target app?", "blue")
    app = "planet"
    app = app.replace(" ", "")

if user_input == "1":
    os.system(f"python scripts/self_explorer.py --app {app} --root_dir {root_dir}")
else:
    demo_timestamp = int(time.time())
    demo_name = datetime.datetime.fromtimestamp(demo_timestamp).strftime(f"demo_{app}_%Y-%m-%d_%H-%M-%S")
    os.system(f"python scripts/step_recorder.py --app {app} --demo {demo_name} --root_dir {root_dir}")
    os.system(f"python scripts/document_generation.py --app {app} --demo {demo_name} --root_dir {root_dir}")
