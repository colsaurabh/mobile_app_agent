import argparse
import ast
import datetime
import json
import os
import re
import sys
import time

import prompts
from config import load_config
from and_controller import list_all_devices, AndroidController, traverse_tree
from model import parse_explore_rsp, parse_grid_rsp, OpenAIModel, GeminiModel
from utils import print_with_color, draw_bbox_multi, draw_grid

arg_desc = "AppAgent Executor"
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, description=arg_desc)
parser.add_argument("--app")
parser.add_argument("--root_dir", default="./")
args = vars(parser.parse_args())

configs = load_config()

if configs["REASONING_MODEL"] == "OpenAI":
    mllm = OpenAIModel(base_url=configs["OPENAI_API_BASE"],
                       api_key=configs["OPENAI_API_KEY"],
                       model=configs["OPENAI_API_MODEL"],
                       temperature=configs["TEMPERATURE"],
                       max_completion_tokens=configs["MAX_COMPLETION_TOKENS"])
elif configs["REASONING_MODEL"] == "Gemini":
    mllm = GeminiModel(api_base=configs["GEMINI_API_BASE"],
                       api_key=configs["GEMINI_API_KEY"],
                       model=configs["GEMINI_API_MODEL"],
                       temperature=configs["TEMPERATURE"],
                       max_completion_tokens=configs["MAX_COMPLETION_TOKENS"])
else:
    print_with_color(f"ERROR: Unsupported model type {configs['MODEL']}!", "red")
    sys.exit()

app = args["app"]
root_dir = args["root_dir"]

if not app:
    print_with_color("What is the name of the app you want me to operate?", "blue")
    app = input()
    app = app.replace(" ", "")

app_dir = os.path.join(os.path.join(root_dir, "apps"), app)
work_dir = os.path.join(root_dir, "tasks")
if not os.path.exists(work_dir):
    os.mkdir(work_dir)
auto_docs_dir = os.path.join(app_dir, "auto_docs")
demo_docs_dir = os.path.join(app_dir, "demo_docs")
task_timestamp = int(time.time())
dir_name = datetime.datetime.fromtimestamp(task_timestamp).strftime(f"task_{app}_%Y-%m-%d_%H-%M-%S")
task_dir = os.path.join(work_dir, dir_name)
os.mkdir(task_dir)
log_path = os.path.join(task_dir, f"log_{app}_{dir_name}.txt")

no_doc = False
if not os.path.exists(auto_docs_dir) and not os.path.exists(demo_docs_dir):
    print_with_color(f"No documentations found for the app {app}. Do you want to proceed with no docs? Enter y or n",
                     "red")
    user_input = ""
    while user_input != "y" and user_input != "n":
        user_input = input().lower()
    if user_input == "y":
        no_doc = True
    else:
        sys.exit()
elif os.path.exists(auto_docs_dir) and os.path.exists(demo_docs_dir):
    # ToDo: Saurabh. Change later to Autonomous & Human
    # print_with_color(f"The app {app} has documentations generated from both autonomous exploration and human "
    #                  f"demonstration. Which one do you want to use? Type 1 or 2.\n1. Autonomous exploration\n2. Human "
    #                  f"Demonstration",
    #                  "blue")
    user_input = "1"
    # while user_input != "1" and user_input != "2":
    #     user_input = input()
    if user_input == "1":
        docs_dir = auto_docs_dir
    else:
        docs_dir = demo_docs_dir
elif os.path.exists(auto_docs_dir):
    print_with_color(f"Documentations generated from autonomous exploration were found for the app {app}. The doc base "
                     f"is selected automatically.", "yellow")
    docs_dir = auto_docs_dir
else:
    print_with_color(f"Documentations generated from human demonstration were found for the app {app}. The doc base is "
                     f"selected automatically.", "yellow")
    docs_dir = demo_docs_dir

device_list = list_all_devices()
if not device_list:
    print_with_color("ERROR: No device found!", "red")
    sys.exit()
print_with_color(f"List of devices attached:\n{str(device_list)}", "yellow")
if len(device_list) == 1:
    device = device_list[0]
    print_with_color(f"Device selected: {device}", "yellow")
else:
    print_with_color("Please choose the Android device to start demo by entering its ID:", "blue")
    device = input()
controller = AndroidController(device)
width, height = controller.get_device_size()
if not width and not height:
    print_with_color("ERROR: Invalid device size!", "red")
    sys.exit()
print_with_color(f"Screen resolution of {device}: {width}x{height}", "yellow")

if configs.get("ENABLE_VOICE", False):
    from utils import voice_ask
    try:
        whisper_model = configs.get("OPENAI_WHISPER_MODEL", "whisper-1")
        task_desc = voice_ask(
            "Please enter the description of the task you want me to complete:",
            api_key=configs["OPENAI_API_KEY"],
            model=whisper_model,
            max_seconds=10
        )
    except Exception:
        print_with_color("Please enter the description of the task you want me to complete:", "blue")
        task_desc = input()
else:
    print_with_color("Please enter the description of the task you want me to complete:", "blue")
    task_desc = input()

round_count = 0
last_act = "None"
task_complete = False
if configs.get("ALWAYS_GRID", False):
    grid_on = True
else:
    grid_on = False
rows, cols = 0, 0


def area_to_xy(area, subarea):
    area -= 1
    row, col = area // cols, area % cols
    x_0, y_0 = col * (width // cols), row * (height // rows)
    if subarea == "top-left":
        x, y = x_0 + (width // cols) // 4, y_0 + (height // rows) // 4
    elif subarea == "top":
        x, y = x_0 + (width // cols) // 2, y_0 + (height // rows) // 4
    elif subarea == "top-right":
        x, y = x_0 + (width // cols) * 3 // 4, y_0 + (height // rows) // 4
    elif subarea == "left":
        x, y = x_0 + (width // cols) // 4, y_0 + (height // rows) // 2
    elif subarea == "right":
        x, y = x_0 + (width // cols) * 3 // 4, y_0 + (height // rows) // 2
    elif subarea == "bottom-left":
        x, y = x_0 + (width // cols) // 4, y_0 + (height // rows) * 3 // 4
    elif subarea == "bottom":
        x, y = x_0 + (width // cols) // 2, y_0 + (height // rows) * 3 // 4
    elif subarea == "bottom-right":
        x, y = x_0 + (width // cols) * 3 // 4, y_0 + (height // rows) * 3 // 4
    else:
        x, y = x_0 + (width // cols) // 2, y_0 + (height // rows) // 2
    return x, y

pending_human_input = None

while round_count < configs["MAX_ROUNDS"]:
    round_count += 1
    print_with_color(f"Round {round_count}", "yellow")
    screenshot_path = controller.get_screenshot(f"{dir_name}_{round_count}", task_dir)
    xml_path = controller.get_xml(f"{dir_name}_{round_count}", task_dir)
    if screenshot_path == "ERROR" or xml_path == "ERROR":
        break

    # This variable will hold the user's answer from the previous round
    human_answer_context = ""
    if pending_human_input:
        human_answer_context = f"You previously asked a question and the human responded with: '{pending_human_input}'. Use this information for your next action."
        pending_human_input = None

    if grid_on:
        rows, cols = draw_grid(screenshot_path, os.path.join(task_dir, f"{dir_name}_{round_count}_grid.png"))
        image = os.path.join(task_dir, f"{dir_name}_{round_count}_grid.png")
        prompt = prompts.task_template_grid
    else:
        clickable_list = []
        focusable_list = []
        traverse_tree(xml_path, clickable_list, "clickable", True)
        traverse_tree(xml_path, focusable_list, "focusable", True)
        elem_list = clickable_list.copy()
        for elem in focusable_list:
            bbox = elem.bbox
            center = (bbox[0][0] + bbox[1][0]) // 2, (bbox[0][1] + bbox[1][1]) // 2
            close = False
            for e in clickable_list:
                bbox = e.bbox
                center_ = (bbox[0][0] + bbox[1][0]) // 2, (bbox[0][1] + bbox[1][1]) // 2
                dist = (abs(center[0] - center_[0]) ** 2 + abs(center[1] - center_[1]) ** 2) ** 0.5
                if dist <= configs["MIN_DIST"]:
                    close = True
                    break
            if not close:
                elem_list.append(elem)
        draw_bbox_multi(screenshot_path, os.path.join(task_dir, f"{dir_name}_{round_count}_labeled.png"), elem_list,
                        dark_mode=configs["DARK_MODE"])
        image = os.path.join(task_dir, f"{dir_name}_{round_count}_labeled.png")
        if no_doc:
            prompt = re.sub(r"<ui_document>", "", prompts.task_template)
        else:
            ui_doc = ""
            for i, elem in enumerate(elem_list):
                doc_path = os.path.join(docs_dir, f"{elem.uid}.txt")
                if not os.path.exists(doc_path):
                    continue
                ui_doc += f"Documentation of UI element labeled with the numeric tag '{i + 1}':\n"
                doc_content = ast.literal_eval(open(doc_path, "r").read())
                if doc_content["tap"]:
                    ui_doc += f"This UI element is clickable. {doc_content['tap']}\n\n"
                if doc_content["text"]:
                    ui_doc += f"This UI element can receive text input. The text input is used for the following " \
                              f"purposes: {doc_content['text']}\n\n"
                if doc_content["long_press"]:
                    ui_doc += f"This UI element is long clickable. {doc_content['long_press']}\n\n"
                if doc_content["v_swipe"]:
                    ui_doc += f"This element can be swiped directly without tapping. You can swipe vertically on " \
                              f"this UI element. {doc_content['v_swipe']}\n\n"
                if doc_content["h_swipe"]:
                    ui_doc += f"This element can be swiped directly without tapping. You can swipe horizontally on " \
                              f"this UI element. {doc_content['h_swipe']}\n\n"
            print_with_color(f"Documentations retrieved for the current interface:\n{ui_doc}", "magenta")
            ui_doc = """
            You also have access to the following documentations that describes the functionalities of UI 
            elements you can interact on the screen. These docs are crucial for you to determine the target of your 
            next action. You should always prioritize these documented elements for interaction:""" + ui_doc
            prompt = re.sub(r"<ui_document>", ui_doc, prompts.task_template)
    prompt = re.sub(r"<task_description>", task_desc, prompt)
    prompt = re.sub(r"<last_act>", last_act, prompt)
    prompt = re.sub(r"<human_answer_context>", human_answer_context, prompt)
    print_with_color("Thinking about what to do in the next step...", "yellow")
    status, rsp = mllm.get_model_response(prompt, [image])
    # print_with_color(f"Status as {status}, Model returned {rsp}", "green")

    if not status or not rsp or rsp.strip() == "":
        print_with_color("Model returned no actionable text. Retrying this round...", "yellow")
        round_count -= 1  # keep the same round index for next attempt
        time.sleep(1.0)
        continue

    if status:
        with open(log_path, "a") as logfile:
            log_item = {"step": round_count, "prompt": prompt, "image": f"{dir_name}_{round_count}_labeled.png",
                        "response": rsp}
            logfile.write(json.dumps(log_item) + "\n")
        if grid_on:
            res = parse_grid_rsp(rsp)
        else:
            res = parse_explore_rsp(rsp)
        act_name = res[0]
        if act_name == "FINISH":
            if configs.get("ENABLE_VOICE", False):
                from utils import voice_ask
                try:
                    whisper_model = configs.get("OPENAI_WHISPER_MODEL", "whisper-1")
                    task_desc = voice_ask(
                        "Please describe your next question or say quit or exit to leave",
                        api_key=configs["OPENAI_API_KEY"],
                        model=whisper_model,
                        max_seconds=10
                    )
                except Exception:
                    print_with_color("Please enter the description of the task you want me to complete:", "blue")
                    task_desc = input()
            else:
                print_with_color("Please enter your next question (or type 'q' or 'Q' to stop):", "blue")
                task_desc = input()

            if task_desc.lower() in ("q", "quit", "exit"):
                task_complete = True
                break                
            last_act = "None"
            continue
        if act_name == "ERROR":
            break
        
        last_act = res[-1]
        res = res[:-1]
    
        if act_name == "tap":
            _, area = res
            tl, br = elem_list[area - 1].bbox
            x, y = (tl[0] + br[0]) // 2, (tl[1] + br[1]) // 2
            ret = controller.tap(x, y)
            if ret == "ERROR":
                print_with_color("ERROR: tap execution failed", "red")
                break
        elif act_name == "text":
            _, input_str = res

            if input_str.strip() == "<HUMAN_INPUT>":
                try:
                    input_str = pending_human_input
                except NameError:
                    print_with_color('No stored input available. Ask first via ask_human("...").', "red")
                    break
            ret = controller.text(input_str)
            if ret == "ERROR":
                print_with_color("ERROR: text execution failed", "red")
                break
        elif act_name == "long_press":
            _, area = res
            tl, br = elem_list[area - 1].bbox
            x, y = (tl[0] + br[0]) // 2, (tl[1] + br[1]) // 2
            ret = controller.long_press(x, y)
            if ret == "ERROR":
                print_with_color("ERROR: long press execution failed", "red")
                break
        elif act_name == "swipe":
            _, area, swipe_dir, dist = res
            tl, br = elem_list[area - 1].bbox
            x, y = (tl[0] + br[0]) // 2, (tl[1] + br[1]) // 2
            ret = controller.swipe(x, y, swipe_dir, dist)
            if ret == "ERROR":
                print_with_color("ERROR: swipe execution failed", "red")
                break
        elif act_name == "grid":
            grid_on = True
        elif act_name == "tap_grid" or act_name == "long_press_grid":
            _, area, subarea = res
            x, y = area_to_xy(area, subarea)
            if act_name == "tap_grid":
                ret = controller.tap(x, y)
                if ret == "ERROR":
                    print_with_color("ERROR: tap execution failed", "red")
                    break
            else:
                ret = controller.long_press(x, y)
                if ret == "ERROR":
                    print_with_color("ERROR: tap execution failed", "red")
                    break
        elif act_name == "swipe_grid":
            _, start_area, start_subarea, end_area, end_subarea = res
            start_x, start_y = area_to_xy(start_area, start_subarea)
            end_x, end_y = area_to_xy(end_area, end_subarea)
            ret = controller.swipe_precise((start_x, start_y), (end_x, end_y))
            if ret == "ERROR":
                print_with_color("ERROR: tap execution failed", "red")
                break
        elif act_name == "ask_human":
            # res = ["ask_human", question, last_act]
            _, question = res
            print_with_color(f"Saurabh: ask_human question is as {question}", "green")
            try:
                if configs.get("ENABLE_VOICE", False):
                    from utils import voice_ask
                    whisper_model = configs.get("OPENAI_WHISPER_MODEL", "whisper-1")
                    answer = voice_ask(
                        question,
                        api_key=configs["OPENAI_API_KEY"],
                        model=whisper_model,
                        max_seconds=10
                    )
                else:
                    print_with_color(question, "blue")
                    answer = input()
            except Exception:
                print_with_color(question, "blue")
                answer = input()

            # # Type the answer (assumes the correct input field is focused by prior action)
            # ret = controller.text(answer)
            # print_with_color(f"Saurabh: ret value is from writting text is: {ret}", "green")
            # if ret == "ERROR":
            #     print_with_color("ERROR: text execution failed after ask_human", "red")
            #     break

            pending_human_input = answer
            print_with_color(f'Saurabh: Captured input. Human input as {pending_human_input}.', "yellow")
            continue

        if act_name != "grid":
            if configs.get("ALWAYS_GRID", False):
                grid_on = True
            else:
                grid_on = False

        time.sleep(configs["REQUEST_INTERVAL"])
    else:
        print_with_color(rsp, "red")
        break

if task_complete:
    print_with_color("Task completed successfully", "yellow")
elif round_count == configs["MAX_ROUNDS"]:
    print_with_color("Task finished due to reaching max rounds", "yellow")
else:
    print_with_color("Task finished unexpectedly", "red")
