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
from and_controller import list_all_devices, AndroidController
from utils import traverse_tree
from model import parse_explore_rsp, parse_grid_rsp, OpenAIModel, GeminiModel
from utils import print_with_color, draw_bbox_multi, draw_grid, area_to_xy, calculate_image_similarity

arg_desc = "AppAgent Executor"
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, description=arg_desc)
parser.add_argument("--app")
parser.add_argument("--root_dir", default="./")
args = vars(parser.parse_args())

try:
    configs = load_config()
except Exception as e:
    print_with_color(f"ERROR: Failed to load configuration: {e}", "red")
    sys.exit(1)

try:
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
        sys.exit(1)
except KeyError as e:
    print_with_color(f"ERROR: Missing required configuration key: {e}", "red")
    sys.exit(1)
except Exception as e:
    print_with_color(f"ERROR: Failed to initialize model: {e}", "red")
    sys.exit(1)

app = args["app"]
root_dir = args["root_dir"]

if not app:
    print_with_color("What is the name of the app you want me to operate?", "blue")
    app = input()
    app = app.replace(" ", "")

try:
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
except OSError as e:
    print_with_color(f"ERROR: Failed to create directories: {e}", "red")
    sys.exit(1)
except Exception as e:
    print_with_color(f"ERROR: Unexpected error during setup: {e}", "red")
    sys.exit(1)

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

try:
    device_list = list_all_devices()
    if not device_list:
        print_with_color("ERROR: No device found!", "red")
        sys.exit(1)
    # print_with_color(f"List of devices attached:\n{str(device_list)}", "yellow")
    
    if len(device_list) == 1:
        device = device_list[0]
        # print_with_color(f"Device selected: {device}", "yellow")
    else:
        print_with_color("Please choose the Android device to start demo by entering its ID:", "blue")
        device = input()
    
    controller = AndroidController(device)
    width, height = controller.get_device_size()
    if not width and not height:
        print_with_color("ERROR: Invalid device size!", "red")
        sys.exit(1)
    # print_with_color(f"Screen resolution of {device}: {width}x{height}", "yellow")
except Exception as e:
    print_with_color(f"ERROR: Device initialization failed: {e}", "red")
    sys.exit(1)

if configs.get("ENABLE_VOICE", False):
    from utils import voice_ask
    try:
        task_desc = voice_ask(
            "Please enter the description of the task to perform.",
            max_seconds=5
        )
    except Exception:
        print_with_color("Please enter the description of the task to perform.", "blue")
        task_desc = input()
else:
    print_with_color("Please enter the description of the task to perform.", "blue")
    task_desc = input()

round_count = 0
last_act = "None"
task_complete = False
if configs.get("ALWAYS_GRID", False):
    grid_on = True
else:
    grid_on = False
rows, cols = 0, 0

disable_xml = configs.get("DISABLE_XML", False)

pending_human_input = None
pending_question = None

# This variable will hold the user's answer from the previous round
human_answer_context = ""

previous_screenshot_path = None
current_screenshot_path = None

while round_count < configs["MAX_ROUNDS"]:
    round_count += 1
    print_with_color(f"Round {round_count}", "yellow")

    try:
        screenshot_path = controller.get_screenshot(f"{dir_name}_{round_count}", task_dir)
        if screenshot_path == "ERROR":
            break

        if not disable_xml:
            xml_path = controller.get_xml(f"{dir_name}_{round_count}", task_dir)
            if xml_path == "ERROR":
                break
    except Exception as e:
        print_with_color(f"ERROR: Screenshot or XML generation failed: {e}", "red")
        sys.exit(1)

    if pending_human_input:
        human_answer_context = f"You previously asked a question {pending_question} and the human responded with: '{pending_human_input}'. Use this information for your next action."
        pending_human_input = None
        pending_question = None

    if grid_on:
        rows, cols = draw_grid(screenshot_path, os.path.join(task_dir, f"{dir_name}_{round_count}_grid.png"))
        image = os.path.join(task_dir, f"{dir_name}_{round_count}_grid.png")
        prompt = prompts.task_template_grid
    else:
        clickable_list = []
        focusable_list = []
        if disable_xml:
            print_with_color("ERROR: XML generation is disabled", "red")
            break

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
            try:
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
            except Exception as e:
                print_with_color(f"ERROR: Documentation fetching failed failed: {e}", "red")
                ui_doc = ""
            # print_with_color(f"Documentations retrieved for the current interface:\n{ui_doc}", "magenta")
            ui_doc = """
            You also have access to the following documentations that describes the functionalities of UI 
            elements you can interact on the screen. These docs are crucial for you to determine the target of your 
            next action. You should always prioritize these documented elements for interaction:""" + ui_doc
            ui_doc = ""
            prompt = re.sub(r"<ui_document>", ui_doc, prompts.task_template)

    # current_screenshot_path = image
    # similarity_score = calculate_image_similarity(previous_screenshot_path, current_screenshot_path)
    # previous_screenshot_path = current_screenshot_path
    # if similarity_score < 0.9:
    #     print_with_color(f"Similarity score is {(similarity_score * 100):.2f}%", "green")
    # else:
    #     print_with_color(f"Similarity score is {(similarity_score * 100):.2f}%", "red")

    prompt = re.sub(r"<task_description>", task_desc, prompt)
    prompt = re.sub(r"<last_act>", last_act, prompt)
    prompt = re.sub(r"<human_answer_context>", human_answer_context, prompt)

    try:
        print_with_color("Thinking about what to do in the next step...", "yellow")
        status, rsp = mllm.get_model_response(prompt, [image])
    except Exception as e:
        print_with_color(f"ERROR: Model request failed: {e}", "red")
        print_with_color("Retrying this round...", "yellow")
        round_count -= 1
        time.sleep(1.0)
        continue

    if not status or not rsp or rsp.strip() == "":
        print_with_color("Model returned no actionable text. Retrying this round...", "yellow")
        round_count -= 1  # keep the same round index for next attempt
        time.sleep(1.0)
        continue

    if status:
        try:
            with open(log_path, "a") as logfile:
                log_item = {"step": round_count, "prompt": prompt, "image": f"{dir_name}_{round_count}_labeled.png",
                            "response": rsp}
                logfile.write(json.dumps(log_item) + "\n")
        except (IOError, OSError) as e:
            print_with_color(f"WARNING: Failed to write to log file: {e}", "yellow")

        try:
            if grid_on:
                res = parse_grid_rsp(rsp)
            else:
                res = parse_explore_rsp(rsp)
        except Exception as e:
            print_with_color(f"ERROR: Failed to parse model response: {e}", "red")
            print_with_color("Retrying this round...", "yellow")
            round_count -= 1
            time.sleep(1.0)
            continue

        act_name = res[0]
        if act_name == "FINISH":
            if configs.get("ENABLE_VOICE", False):
                from utils import voice_ask
                try:
                    task_desc = voice_ask(
                        "Please describe your next question or say quit or exit to stop",
                        max_seconds=5
                    )
                except Exception:
                    print_with_color("Please enter the description of the task to perform.", "blue")
                    task_desc = input()
            else:
                print_with_color("Please enter the next task (or type 'q' or 'Q' or quit or exit to stop):", "blue")
                task_desc = input()

            if task_desc.lower() in ("q", "quit", "exit"):
                task_complete = True
                break                
            last_act = "None"
            continue
        if act_name == "ERROR":
            continue
        
        last_act = res[-1]
        res = res[:-1]
    
        if act_name == "tap":
            try:
                _, area = res
                if area < 1 or area > len(elem_list):
                    print_with_color(f"ERROR: Invalid area index {area}. Available areas: 1-{len(elem_list)}", "red")
                    continue
                tl, br = elem_list[area - 1].bbox
                x, y = (tl[0] + br[0]) // 2, (tl[1] + br[1]) // 2
                ret = controller.tap(x, y)
                if ret == "ERROR":
                    print_with_color("ERROR: tap execution failed", "red")
                    continue
            except (IndexError, ValueError) as e:
                print_with_color(f"ERROR: Invalid tap parameters: {e}", "red")
                continue
            except Exception as e:
                print_with_color(f"ERROR: Unexpected error during tap: {e}", "red")
                continue
        elif act_name == "text":
            # Saurabh: Check this code
            try:
                _, input_str = res
                
                if input_str.strip() == "<HUMAN_INPUT>":
                    try:
                        input_str = pending_human_input
                        if input_str is None:
                            print_with_color('No stored input available. Ask first via ask_human("...").', "red")
                            continue
                    except NameError:
                        print_with_color('No stored input available. Ask first via ask_human("...").', "red")
                        continue
                
                ret = controller.text(input_str)
                if ret == "ERROR":
                    print_with_color("ERROR: text execution failed", "red")
                    continue

                ret = controller.tap(width // 2, height // 10)
                # Tapping to close the keyboard
                if ret == "ERROR":
                    print_with_color("ERROR: tap execution failed for keyboard dismissal", "red")
                    continue
            except (ValueError, TypeError) as e:
                print_with_color(f"ERROR: Invalid text parameters: {e}", "red")
                continue
            except Exception as e:
                print_with_color(f"ERROR: Unexpected error during text input: {e}", "red")
                continue
        elif act_name == "long_press":
            try:
                _, area = res
                if area < 1 or area > len(elem_list):
                    print_with_color(f"ERROR: Invalid area index {area}. Available areas: 1-{len(elem_list)}", "red")
                    continue
                tl, br = elem_list[area - 1].bbox
                x, y = (tl[0] + br[0]) // 2, (tl[1] + br[1]) // 2
                ret = controller.long_press(x, y)
                if ret == "ERROR":
                    print_with_color("ERROR: long press execution failed", "red")
                    continue
            except (IndexError, ValueError) as e:
                print_with_color(f"ERROR: Invalid long press parameters: {e}", "red")
                continue
            except Exception as e:
                print_with_color(f"ERROR: Unexpected error during long press: {e}", "red")
                continue
        elif act_name == "swipe":
            try:
                _, area, swipe_dir, dist = res
                
                if area < 1 or area > len(elem_list):
                    print_with_color(f"ERROR: Invalid area index {area}. Available areas: 1-{len(elem_list)}", "red")
                    continue
                    
                tl, br = elem_list[area - 1].bbox
                x, y = (tl[0] + br[0]) // 2, (tl[1] + br[1]) // 2
                
                # Validate swipe direction and distance
                if swipe_dir not in ["up", "down", "left", "right"]:
                    print_with_color(f"ERROR: Invalid swipe direction '{swipe_dir}'. Must be up, down, left, or right", "red")
                    continue
                
                ret = controller.swipe(x, y, swipe_dir, dist)
                if ret == "ERROR":
                    print_with_color("ERROR: swipe execution failed", "red")
                    continue
            except (IndexError, ValueError, TypeError) as e:
                print_with_color(f"ERROR: Invalid swipe parameters: {e}", "red")
                continue
            except Exception as e:
                print_with_color(f"ERROR: Unexpected error during swipe: {e}", "red")
                continue
        elif act_name == "grid":
            grid_on = True
        elif act_name == "tap_grid" or act_name == "long_press_grid":
            try:
                _, area, subarea = res
                
                # Validate area bounds
                if area < 1 or area > (rows * cols):
                    print_with_color(f"ERROR: Invalid grid area {area}. Available areas: 1-{rows * cols}", "red")
                    continue
                    
                # Validate subarea
                valid_subareas = ["top-left", "top", "top-right", "left", "center", "right", "bottom-left", "bottom", "bottom-right"]
                if subarea not in valid_subareas:
                    print_with_color(f"ERROR: Invalid subarea '{subarea}'. Must be one of: {', '.join(valid_subareas)}", "red")
                    continue
                
                x, y = area_to_xy(area, subarea, height, width, rows, cols)
                
                # Check if area_to_xy returned valid coordinates
                if x is None or y is None:
                    print_with_color("ERROR: Failed to calculate grid coordinates", "red")
                    continue
                
                if act_name == "tap_grid":
                    ret = controller.tap(x, y)
                    if ret == "ERROR":
                        print_with_color("ERROR: grid tap execution failed", "red")
                        continue
                else:  # long_press_grid
                    ret = controller.long_press(x, y)
                    if ret == "ERROR":
                        print_with_color("ERROR: grid long press execution failed", "red")
                        continue
            except (ValueError, TypeError) as e:
                print_with_color(f"ERROR: Invalid grid action parameters: {e}", "red")
                continue
            except Exception as e:
                print_with_color(f"ERROR: Unexpected error during grid action: {e}", "red")
                continue
        elif act_name == "swipe_grid":
            try:
                _, start_area, start_subarea, end_area, end_subarea = res
                
                # Validate area bounds
                max_areas = rows * cols
                if start_area < 1 or start_area > max_areas:
                    print_with_color(f"ERROR: Invalid start area {start_area}. Available areas: 1-{max_areas}", "red")
                    continue
                if end_area < 1 or end_area > max_areas:
                    print_with_color(f"ERROR: Invalid end area {end_area}. Available areas: 1-{max_areas}", "red")
                    continue
                
                # Validate subareas
                valid_subareas = ["top-left", "top", "top-right", "left", "center", "right", "bottom-left", "bottom", "bottom-right"]
                if start_subarea not in valid_subareas:
                    print_with_color(f"ERROR: Invalid start subarea '{start_subarea}'. Must be one of: {', '.join(valid_subareas)}", "red")
                    continue
                if end_subarea not in valid_subareas:
                    print_with_color(f"ERROR: Invalid end subarea '{end_subarea}'. Must be one of: {', '.join(valid_subareas)}", "red")
                    continue
                
                start_x, start_y = area_to_xy(start_area, start_subarea, height, width, rows, cols)
                end_x, end_y = area_to_xy(end_area, end_subarea, height, width, rows, cols)
                
                # Check if area_to_xy returned valid coordinates
                if start_x is None or start_y is None or end_x is None or end_y is None:
                    print_with_color("ERROR: Failed to calculate grid coordinates for swipe", "red")
                    continue
                
                ret = controller.swipe_precise((start_x, start_y), (end_x, end_y))
                if ret == "ERROR":
                    print_with_color("ERROR: grid swipe execution failed", "red")
                    continue
            except (ValueError, TypeError) as e:
                print_with_color(f"ERROR: Invalid grid swipe parameters: {e}", "red")
                continue
            except Exception as e:
                print_with_color(f"ERROR: Unexpected error during grid swipe: {e}", "red")
                continue
        elif act_name == "ask_human":
            # res = ["ask_human", question, last_act]
            _, question = res
            try:
                if configs.get("ENABLE_VOICE", False):
                    from utils import voice_ask
                    answer = voice_ask(
                        question,
                        max_seconds=3
                    )
                else:
                    print_with_color(question, "blue")
                    answer = input()
            except Exception:
                print_with_color(question, "blue")
                answer = input()

            pending_human_input = answer
            pending_question = question
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
