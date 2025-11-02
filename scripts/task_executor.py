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
from device_controller import list_all_devices, DeviceController
from utils import traverse_tree
from model import parse_explore_rsp, parse_grid_rsp, OpenAIModel, GeminiModel
from utils import draw_bbox_multi, draw_grid, area_to_xy, calculate_image_similarity
from logging_controller import get_logger

arg_desc = "AppAgent Executor"
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, description=arg_desc)
parser.add_argument("--app")
parser.add_argument("--root_dir", default="./")
args = vars(parser.parse_args())

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
        logger.error(f"ERROR: Unsupported model type {configs['MODEL']}!")
        sys.exit(1)
except KeyError as e:
    logger.error(f"ERROR: Missing required configuration key: {e}")
    sys.exit(1)
except Exception as e:
    logger.error(f"ERROR: Failed to initialize model: {e}")
    sys.exit(1)

app = args["app"]
root_dir = args["root_dir"]

if not app:
    logger.show("What is the name of the app you want me to operate?")
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
    logger.error(f"ERROR: Failed to create directories: {e}")
    sys.exit(1)
except Exception as e:
    logger.error(f"ERROR: Unexpected error during setup: {e}")
    sys.exit(1)

no_doc = False
if not os.path.exists(auto_docs_dir) and not os.path.exists(demo_docs_dir):
    logger.show(f"No documentations found for the app {app}. Do you want to proceed with no docs? Enter y or n")
    user_input = ""
    while user_input != "y" and user_input != "n":
        user_input = input().lower()
    if user_input == "y":
        no_doc = True
    else:
        sys.exit()
elif os.path.exists(auto_docs_dir) and os.path.exists(demo_docs_dir):
    # ToDo: Saurabh. Change later to Autonomous & Human
    # logger.show(f"The app {app} has documentations generated from both autonomous exploration and human "
    #                  f"demonstration. Which one do you want to use? Type 1 or 2.\n1. Autonomous exploration\n2. Human "
    #                  f"Demonstration")
    user_input = "1"
    # while user_input != "1" and user_input != "2":
    #     user_input = input()
    if user_input == "1":
        docs_dir = auto_docs_dir
    else:
        docs_dir = demo_docs_dir
elif os.path.exists(auto_docs_dir):
    logger.info(f"Documentations generated from autonomous exploration were found for the app {app}. The doc base "
                     f"is selected automatically.")
    docs_dir = auto_docs_dir
else:
    logger.info(f"Documentations generated from human demonstration were found for the app {app}. The doc base is "
                     f"selected automatically.", "yellow")
    docs_dir = demo_docs_dir

try:
    device_list = list_all_devices()
    if not device_list:
        logger.error("ERROR: No device found!")
        sys.exit(1)
    # logger.debug(f"List of devices attached:\n{str(device_list)}")
    
    if len(device_list) == 1:
        device = device_list[0]
    elif len(device_list) > 1:
        device_list = configs.get("ANDROID_DEVICES", ["10BE8N1N5200203"])
        device = device_list[0]
    else:
        logger.show("Please choose the Android device to start demo by entering its ID")
        device = input()
    logger.debug(f"Device selected: {device}")
    
    controller = DeviceController(device)
    width, height = controller.get_device_size()
    if not width and not height:
        logger.error("ERROR: Invalid device size!")
        sys.exit(1)
    # logger.debug(f"Screen resolution of {device}: {width}x{height}")
except Exception as e:
    logger.error(f"ERROR: Device initialization failed: {e}")
    sys.exit(1)

if configs.get("ENABLE_VOICE", False):
    from utils import voice_ask
    try:
        task_desc = voice_ask(
            "Please enter the description of the task to perform.",
            max_seconds=5
        )
    except Exception:
        logger.show("Please enter the description of the task to perform.")
        task_desc = input()
else:
    logger.show("Please enter the description of the task to perform.")
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
special_action_used = False
special_action_context = ""

# This variable will hold the user's answer from the previous round
human_answer_context = ""

previous_screenshot_path = None
current_screenshot_path = None

human_override_triggered = False
human_override_context = ""

human_override = configs.get("ENABLE_HUMAN_OVERRIDE", False)
if human_override:
    import threading
    from pynput import keyboard
    def on_press(key):
        """Trigger human override when human_override_key is pressed."""
        global human_override_triggered
        try:
            human_override_key = configs.get("HUMAN_OVERRIDE_KEY", "|")
            if hasattr(key, 'char') and key.char == human_override_key:
                human_override_triggered = True
                logger.debug(f"Human override triggered via '{human_override_key}' key.")
        except Exception:
            pass

    def listen_for_human_key():
        """Background listener for key press."""
        with keyboard.Listener(on_press=on_press) as listener:
            listener.join()

    key_thread = threading.Thread(target=listen_for_human_key, daemon=True)
    key_thread.start()

while round_count < configs["MAX_ROUNDS"]:
    round_count += 1
    logger.info(f"Round {round_count}")

    try:
        screenshot_path = controller.get_screenshot(f"{dir_name}_{round_count}", task_dir)
        if screenshot_path == "ERROR":
            break

        if not disable_xml:
            xml_path = controller.get_xml(f"{dir_name}_{round_count}", task_dir)
            if xml_path == "ERROR":
                break
    except Exception as e:
        logger.error(f"ERROR: Screenshot or XML generation failed: {e}")
        sys.exit(1)

    if pending_human_input:
        human_answer_context = f"You previously asked a question {pending_question} and the human responded with: '{pending_human_input}'. Use this information for your next action."
        pending_human_input = None
        pending_question = None

    if human_override_triggered:
        logger.debug("Human intervention triggered via human_override_triggered")
        human_override_context = f"VERY IMPORTANT: Human intervention triggered. You should leave the current action and ask human for the next action. Question to ask: **What should I do next?**"
        human_override_triggered = False

    if grid_on:
        rows, cols = draw_grid(screenshot_path, os.path.join(task_dir, f"{dir_name}_{round_count}_grid.png"))
        image = os.path.join(task_dir, f"{dir_name}_{round_count}_grid.png")
        prompt = prompts.task_template_grid
    else:
        clickable_list = []
        focusable_list = []
        if disable_xml:
            logger.error("ERROR: XML generation is disabled")
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
                logger.error(f"ERROR: Documentation fetching failed failed: {e}")
                ui_doc = ""
            # logger.info(f"Documentations retrieved for the current interface:\n{ui_doc}")
            ui_doc = """
            You also have access to the following documentations that describes the functionalities of UI 
            elements you can interact on the screen. These docs are crucial for you to determine the target of your 
            next action. You should always prioritize these documented elements for interaction:""" + ui_doc
            ui_doc = ""
            prompt = re.sub(r"<ui_document>", ui_doc, prompts.task_template)

    use_similarity = configs.get("USE_SIMILARITY_COMPARISION", True)
    if use_similarity:
        current_screenshot_path = image
        similarity_score = calculate_image_similarity(previous_screenshot_path, current_screenshot_path)
        if similarity_score > 0.99:
            if not special_action_used:
                logger.debug(f"Screen unchanged; taking special recovery action (swipe up). Score is: {(similarity_score * 100):.2f}%")
                special_action_used = True
                special_action_context = "The previous action did not change the screen. Its imp to swipe up the screen from middle to see data before continuing \n"
            else:
                logger.debug(f"High similarity detected again but special_action_used already true. Score is: {(similarity_score * 100):.2f}%")
        else:
            logger.debug(f"Similarity score low and resetting special_action_used. Score is: {(similarity_score * 100):.2f}%")
            special_action_used = False
            special_action_context = ""
        previous_screenshot_path = current_screenshot_path

    prompt = re.sub(r"<task_description>", task_desc, prompt)
    prompt = re.sub(r"<last_act>", last_act, prompt)
    prompt = re.sub(r"<human_answer_context>", human_answer_context, prompt)
    prompt = re.sub(r"<recovery_context>", special_action_context, prompt)

    if human_override_context:
        logger.debug("Human intervention sending to llm prompt")
        prompt = re.sub(r"<human_override_context>", human_override_context, prompt)
        human_override_context = ""

    try:
        logger.info("Thinking about what to do in the next step...")
        status, rsp = mllm.get_model_response(prompt, [image])
    except Exception as e:
        logger.error(f"ERROR: Model request failed: {e}")
        logger.info("Retrying this round...")
        round_count -= 1
        time.sleep(1.0)
        continue

    if not status or not rsp or rsp.strip() == "":
        logger.info("Model returned no actionable text. Retrying this round...")
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
            logger.warning(f"WARNING: Failed to write to log file: {e}")

        try:
            if grid_on:
                res = parse_grid_rsp(rsp)
            else:
                res = parse_explore_rsp(rsp)
        except Exception as e:
            logger.error(f"ERROR: Failed to parse model response: {e}")
            logger.info("Retrying this round...")
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
                    logger.show("Please enter the description of the task to perform.")
                    task_desc = input()
            else:
                logger.show("Please enter the next task (or type 'q' or 'Q' or quit or exit to stop):")
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
                    logger.warning(f"ERROR: Invalid area index {area}. Available areas: 1-{len(elem_list)}")
                    continue
                tl, br = elem_list[area - 1].bbox
                x, y = (tl[0] + br[0]) // 2, (tl[1] + br[1]) // 2
                ret = controller.tap(x, y)
                if ret == "ERROR":
                    logger.warning("ERROR: tap execution failed")
                    continue
            except (IndexError, ValueError) as e:
                logger.error(f"ERROR: Invalid tap parameters: {e}")
                continue
            except Exception as e:
                logger.error(f"ERROR: Unexpected error during tap: {e}")
                continue
        elif act_name == "text":
            # Saurabh: Check this code
            try:
                _, input_str = res
                
                if input_str.strip() == "<HUMAN_INPUT>":
                    try:
                        input_str = pending_human_input
                        if input_str is None:
                            logger.warning('No stored input available. Ask first via ask_human("...").')
                            continue
                    except NameError:
                        logger.warning('No stored input available. Ask first via ask_human("...").')
                        continue
                
                ret = controller.text(input_str)
                if ret == "ERROR":
                    logger.error("ERROR: text execution failed")
                    continue

                ret = controller.tap(width // 2, height // 10)
                # Tapping to close the keyboard
                if ret == "ERROR":
                    logger.error("ERROR: tap execution failed for keyboard dismissal")
                    continue
            except (ValueError, TypeError) as e:
                logger.error(f"ERROR: Invalid text parameters: {e}")
                continue
            except Exception as e:
                logger.error(f"ERROR: Unexpected error during text input: {e}")
                continue
        elif act_name == "long_press":
            try:
                _, area = res
                if area < 1 or area > len(elem_list):
                    logger.warning(f"ERROR: Invalid area index {area}. Available areas: 1-{len(elem_list)}")
                    continue
                tl, br = elem_list[area - 1].bbox
                x, y = (tl[0] + br[0]) // 2, (tl[1] + br[1]) // 2
                ret = controller.long_press(x, y)
                if ret == "ERROR":
                    logger.error("ERROR: long press execution failed")
                    continue
            except (IndexError, ValueError) as e:
                logger.error(f"ERROR: Invalid long press parameters: {e}")
                continue
            except Exception as e:
                logger.error(f"ERROR: Unexpected error during long press: {e}")
                continue
        elif act_name == "swipe":
            try:
                _, area, swipe_dir, dist = res
                
                if area < 1 or area > len(elem_list):
                    logger.warning(f"ERROR: Invalid area index {area}. Available areas: 1-{len(elem_list)}")
                    continue
                    
                tl, br = elem_list[area - 1].bbox
                x, y = (tl[0] + br[0]) // 2, (tl[1] + br[1]) // 2
                
                # Validate swipe direction and distance
                if swipe_dir not in ["up", "down", "left", "right"]:
                    logger.warning(f"ERROR: Invalid swipe direction '{swipe_dir}'. Must be up, down, left, or right")
                    continue
                
                ret = controller.swipe(x, y, swipe_dir, dist)
                if ret == "ERROR":
                    logger.error("ERROR: swipe execution failed")
                    continue
            except (IndexError, ValueError, TypeError) as e:
                logger.error(f"ERROR: Invalid swipe parameters: {e}")
                continue
            except Exception as e:
                logger.error(f"ERROR: Unexpected error during swipe: {e}")
                continue
        elif act_name == "grid":
            grid_on = True
        elif act_name == "tap_grid" or act_name == "long_press_grid":
            try:
                _, area, subarea = res
                
                # Validate area bounds
                if area < 1 or area > (rows * cols):
                    logger.warning(f"ERROR: Invalid area index {area}. Available areas: 1-{len(elem_list)}")
                    continue
                    
                # Validate subarea
                valid_subareas = ["top-left", "top", "top-right", "left", "center", "right", "bottom-left", "bottom", "bottom-right"]
                if subarea not in valid_subareas:
                    logger.warning(f"ERROR: Invalid subarea '{subarea}'. Must be one of: {', '.join(valid_subareas)}")
                    continue
                
                x, y = area_to_xy(area, subarea, height, width, rows, cols)
                
                # Check if area_to_xy returned valid coordinates
                if x is None or y is None:
                    logger.warning("ERROR: Failed to calculate grid coordinates")
                    continue
                
                if act_name == "tap_grid":
                    ret = controller.tap(x, y)
                    if ret == "ERROR":
                        logger.error("ERROR: grid tap execution failed")
                        continue
                else:  # long_press_grid
                    ret = controller.long_press(x, y)
                    if ret == "ERROR":
                        logger.error("ERROR: grid long press execution failed")
                        continue
            except (ValueError, TypeError) as e:
                logger.error(f"ERROR: Invalid grid action parameters: {e}")
                continue
            except Exception as e:
                logger.error(f"ERROR: Unexpected error during grid action: {e}")
                continue
        elif act_name == "swipe_grid":
            try:
                _, start_area, start_subarea, end_area, end_subarea = res
                
                # Validate area bounds
                max_areas = rows * cols
                if start_area < 1 or start_area > max_areas:
                    logger.warning(f"ERROR: Invalid start area {start_area}. Available areas: 1-{max_areas}")
                    continue
                if end_area < 1 or end_area > max_areas:
                    logger.warning(f"ERROR: Invalid end area {end_area}. Available areas: 1-{max_areas}")
                    continue
                
                # Validate subareas
                valid_subareas = ["top-left", "top", "top-right", "left", "center", "right", "bottom-left", "bottom", "bottom-right"]
                if start_subarea not in valid_subareas:
                    logger.warning(f"ERROR: Invalid start subarea '{start_subarea}'. Must be one of: {', '.join(valid_subareas)}")
                    continue
                if end_subarea not in valid_subareas:
                    logger.warning(f"ERROR: Invalid end subarea '{end_subarea}'. Must be one of: {', '.join(valid_subareas)}")
                    continue
                
                start_x, start_y = area_to_xy(start_area, start_subarea, height, width, rows, cols)
                end_x, end_y = area_to_xy(end_area, end_subarea, height, width, rows, cols)
                
                # Check if area_to_xy returned valid coordinates
                if start_x is None or start_y is None or end_x is None or end_y is None:
                    logger.warning("ERROR: Failed to calculate grid coordinates for swipe")
                    continue
                
                ret = controller.swipe_precise((start_x, start_y), (end_x, end_y))
                if ret == "ERROR":
                    logger.error("ERROR: grid swipe execution failed")
                    continue
            except (ValueError, TypeError) as e:
                logger.error(f"ERROR: Invalid grid swipe parameters: {e}")
                continue
            except Exception as e:
                logger.error(f"ERROR: Unexpected error during grid swipe: {e}")
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
                    logger.show(question)
                    answer = input()
            except Exception:
                logger.show(question)
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
        logger.error(rsp)
        break

if task_complete:
    logger.show("Task completed successfully")
elif round_count == configs["MAX_ROUNDS"]:
    logger.info("Task finished due to reaching max rounds")
else:
    logger.error("Task finished unexpectedly")
