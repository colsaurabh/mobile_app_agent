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
from model import parse_explore_rsp, parse_reflect_rsp, OpenAIModel, GeminiModel
from utils import print_with_color, draw_bbox_multi

arg_desc = "AppAgent - Autonomous Exploration"
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
    print_with_color("What is the name of the target app?", "blue")
    app = input()
    app = app.replace(" ", "")

work_dir = os.path.join(root_dir, "apps")
if not os.path.exists(work_dir):
    os.mkdir(work_dir)
work_dir = os.path.join(work_dir, app)
if not os.path.exists(work_dir):
    os.mkdir(work_dir)
demo_dir = os.path.join(work_dir, "demos")
if not os.path.exists(demo_dir):
    os.mkdir(demo_dir)
demo_timestamp = int(time.time())
task_name = datetime.datetime.fromtimestamp(demo_timestamp).strftime("self_explore_%Y-%m-%d_%H-%M-%S")
task_dir = os.path.join(demo_dir, task_name)
os.mkdir(task_dir)
docs_dir = os.path.join(work_dir, "auto_docs")
if not os.path.exists(docs_dir):
    os.mkdir(docs_dir)
explore_log_path = os.path.join(task_dir, f"log_explore_{task_name}.txt")
reflect_log_path = os.path.join(task_dir, f"log_reflect_{task_name}.txt")

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
controller = DeviceController(device)
width, height = controller.get_device_size()
if not width and not height:
    print_with_color("ERROR: Invalid device size!", "red")
    sys.exit()
print_with_color(f"Screen resolution of {device}: {width}x{height}", "yellow")

print_with_color("Please enter the description of the task you want me to complete:", "blue")
task_desc = input()

round_count = 0
doc_count = 0
useless_list = set()
last_act = "None"
task_complete = False
while round_count < configs["MAX_ROUNDS"]:
    round_count += 1
    print_with_color(f"Round {round_count}", "yellow")
    # screenshot_before = controller.get_screenshot(f"{round_count}_before", task_dir)
    # xml_path = controller.get_xml(f"{round_count}", task_dir)
    # if screenshot_before == "ERROR" or xml_path == "ERROR":
    #     break
    # clickable_list = []
    # focusable_list = []
    # traverse_tree(xml_path, clickable_list, "clickable", True)
    # traverse_tree(xml_path, focusable_list, "focusable", True)
    # elem_list = []
    # for elem in clickable_list:
    #     if elem.uid in useless_list:
    #         continue
    #     elem_list.append(elem)
    # for elem in focusable_list:
    #     if elem.uid in useless_list:
    #         continue
    #     bbox = elem.bbox
    #     center = (bbox[0][0] + bbox[1][0]) // 2, (bbox[0][1] + bbox[1][1]) // 2
    #     close = False
    #     for e in clickable_list:
    #         bbox = e.bbox
    #         center_ = (bbox[0][0] + bbox[1][0]) // 2, (bbox[0][1] + bbox[1][1]) // 2
    #         dist = (abs(center[0] - center_[0]) ** 2 + abs(center[1] - center_[1]) ** 2) ** 0.5
    #         if dist <= configs["MIN_DIST"]:
    #             close = True
    #             break
    #     if not close:
    #         elem_list.append(elem)
    # draw_bbox_multi(screenshot_before, os.path.join(task_dir, f"{round_count}_before_labeled.png"), elem_list,
    #                 dark_mode=configs["DARK_MODE"])



    # screenshot_before = controller.get_screenshot(f"{round_count}_before", task_dir)
    # xml_path = controller.get_xml(f"{round_count}", task_dir)
    # if screenshot_before == "ERROR" or xml_path == "ERROR":
    #     break

    # # Collect a broader set of interactive candidates
    # clickable_list = []
    # focusable_list = []
    # long_clickable_list = []
    # scrollable_list = []

    # traverse_tree(xml_path, clickable_list, "clickable", True)
    # traverse_tree(xml_path, focusable_list, "focusable", True)
    # traverse_tree(xml_path, long_clickable_list, "long-clickable", True)
    # traverse_tree(xml_path, scrollable_list, "scrollable", True)

    # # Merge with relaxed de-duplication (by IoU, not just center distance)
    # def iou(boxA, boxB):
    #     (ax1, ay1), (ax2, ay2) = boxA
    #     (bx1, by1), (bx2, by2) = boxB
    #     x_left = max(ax1, bx1)
    #     y_top = max(ay1, by1)
    #     x_right = min(ax2, bx2)
    #     y_bottom = min(ay2, by2)
    #     if x_right <= x_left or y_bottom <= y_top:
    #         return 0.0
    #     inter = (x_right - x_left) * (y_bottom - y_top)
    #     areaA = (ax2 - ax1) * (ay2 - ay1)
    #     areaB = (bx2 - bx1) * (by2 - by1)
    #     return inter / float(areaA + areaB - inter + 1e-6)

    # merged = []
    # def add_if_new(e):
    #     for m in merged:
    #         if iou(m.bbox, e.bbox) > 0.6:
    #             return
    #     merged.append(e)

    # for e in clickable_list:
    #     add_if_new(e)
    # for e in focusable_list:
    #     add_if_new(e)
    # for e in long_clickable_list:
    #     add_if_new(e)
    # for e in scrollable_list:
    #     add_if_new(e)

    # # Optional: drop very tiny boxes (noise)
    # elem_list = [e for e in merged if (e.bbox[1][0]-e.bbox[0][0]) * (e.bbox[1][1]-e.bbox[0][1]) > 2000]


    dir_name = datetime.datetime.fromtimestamp(int(time.time())).strftime(f"task_{app}_%Y-%m-%d_%H-%M-%S")
    screenshot_before = controller.get_screenshot(f"{dir_name}_{round_count}_before", task_dir)
    # xml_path = controller.get_xml(f"{round_count}", task_dir)
    xml_path = controller.get_xml(f"{dir_name}_{round_count}", task_dir)

    # xml_path = controller.get_xml(f"{dir_name}_{round_count}", task_dir)
    if screenshot_before == "ERROR" or xml_path == "ERROR":
        break
    from utils import collect_interactive_elements
    elem_list = []
    elem_list = collect_interactive_elements(xml_path, min_area=2000, iou_thresh=0.6)
    print_with_color(f"Detected {len(elem_list)} interactive elements", "green")

    draw_bbox_multi(screenshot_before, os.path.join(task_dir, f"{dir_name}_{round_count}_before_labeled.png"), elem_list,
                    dark_mode=configs["DARK_MODE"])

    prompt = re.sub(r"<task_description>", task_desc, prompts.self_explore_task_template)
    prompt = re.sub(r"<last_act>", last_act, prompt)
    base64_img_before = os.path.join(task_dir, f"{dir_name}_{round_count}_before_labeled.png")
    print_with_color("Thinking about what to do in the next step...", "yellow")
    status, rsp = mllm.get_model_response(prompt, [base64_img_before])

    if status:
        with open(explore_log_path, "a") as logfile:
            log_item = {"step": round_count, "prompt": prompt, "image": f"{dir_name}_{round_count}_before_labeled.png",
                        "response": rsp}
            logfile.write(json.dumps(log_item) + "\n")
        res = parse_explore_rsp(rsp)
        act_name = res[0]
        last_act = res[-1]
        res = res[:-1]
        if act_name == "FINISH":
            task_complete = True
            break
        if act_name == "tap":
            _, area = res
            if not isinstance(area, int) or area < 1 or area > len(elem_list):
                print_with_color(f"Invalid element index: {area}. Valid range is 1..{len(elem_list)}.", "red")
                last_act = "None"
                time.sleep(configs["REQUEST_INTERVAL"])
                continue
            tl, br = elem_list[area - 1].bbox
            x, y = (tl[0] + br[0]) // 2, (tl[1] + br[1]) // 2
            ret = controller.tap(x, y)
            if ret == "ERROR":
                print_with_color("ERROR: tap execution failed", "red")
                break
        elif act_name == "text":
            _, input_str = res
            ret = controller.text(input_str)
            if ret == "ERROR":
                print_with_color("ERROR: text execution failed", "red")
                break
        elif act_name == "long_press":
            _, area = res
            if not isinstance(area, int) or area < 1 or area > len(elem_list):
                print_with_color(f"Invalid element index: {area}. Valid range is 1..{len(elem_list)}.", "red")
                last_act = "None"
                time.sleep(configs["REQUEST_INTERVAL"])
                continue
            tl, br = elem_list[area - 1].bbox
            x, y = (tl[0] + br[0]) // 2, (tl[1] + br[1]) // 2
            ret = controller.long_press(x, y)
            if ret == "ERROR":
                print_with_color("ERROR: long press execution failed", "red")
                break
        elif act_name == "swipe":
            _, area, swipe_dir, dist = res
            if not isinstance(area, int) or area < 1 or area > len(elem_list):
                print_with_color(f"Invalid element index: {area}. Valid range is 1..{len(elem_list)}.", "red")
                last_act = "None"
                time.sleep(configs["REQUEST_INTERVAL"])
                continue
            tl, br = elem_list[area - 1].bbox
            x, y = (tl[0] + br[0]) // 2, (tl[1] + br[1]) // 2
            ret = controller.swipe(x, y, swipe_dir, dist)
            if ret == "ERROR":
                print_with_color("ERROR: swipe execution failed", "red")
                break
        else:
            break
        time.sleep(configs["REQUEST_INTERVAL"])
    else:
        print_with_color(rsp, "red")
        break

    screenshot_after = controller.get_screenshot(f"{dir_name}_{round_count}_after", task_dir)
    if screenshot_after == "ERROR":
        break
    draw_bbox_multi(screenshot_after, os.path.join(task_dir, f"{dir_name}_{round_count}_after_labeled.png"), elem_list,
                    dark_mode=configs["DARK_MODE"])
    base64_img_after = os.path.join(task_dir, f"{dir_name}_{round_count}_after_labeled.png")

    if act_name == "tap":
        prompt = re.sub(r"<action>", "tapping", prompts.self_explore_reflect_template)
    elif act_name == "text":
        continue
    elif act_name == "long_press":
        prompt = re.sub(r"<action>", "long pressing", prompts.self_explore_reflect_template)
    elif act_name == "swipe":
        swipe_dir = res[2]
        if swipe_dir == "up" or swipe_dir == "down":
            act_name = "v_swipe"
        elif swipe_dir == "left" or swipe_dir == "right":
            act_name = "h_swipe"
        prompt = re.sub(r"<action>", "swiping", prompts.self_explore_reflect_template)
    else:
        print_with_color("ERROR: Undefined act!", "red")
        break
    prompt = re.sub(r"<ui_element>", str(area), prompt)
    prompt = re.sub(r"<task_desc>", task_desc, prompt)
    prompt = re.sub(r"<last_act>", last_act, prompt)

    print_with_color("Reflecting on my previous action...", "yellow")
    status, rsp = mllm.get_model_response(prompt, [base64_img_before, base64_img_after])
    if status:
        resource_id = elem_list[int(area) - 1].uid
        with open(reflect_log_path, "a") as logfile:
            log_item = {"step": round_count, "prompt": prompt, "image_before": f"{round_count}_before_labeled.png",
                        "image_after": f"{round_count}_after.png", "response": rsp}
            logfile.write(json.dumps(log_item) + "\n")
        res = parse_reflect_rsp(rsp)
        decision = res[0]
        if decision == "ERROR":
            break
        if decision == "INEFFECTIVE":
            useless_list.add(resource_id)
            last_act = "None"
        elif decision == "BACK" or decision == "CONTINUE" or decision == "SUCCESS":
            if decision == "BACK" or decision == "CONTINUE":
                useless_list.add(resource_id)
                last_act = "None"
                if decision == "BACK":
                    ret = controller.back()
                    if ret == "ERROR":
                        print_with_color("ERROR: back execution failed", "red")
                        break
            doc = res[-1]
            doc_name = resource_id + ".txt"
            doc_path = os.path.join(docs_dir, doc_name)
            if os.path.exists(doc_path):
                doc_content = ast.literal_eval(open(doc_path).read())
                if doc_content[act_name]:
                    print_with_color(f"Documentation for the element {resource_id} already exists.", "yellow")
                    continue
            else:
                doc_content = {
                    "tap": "",
                    "text": "",
                    "v_swipe": "",
                    "h_swipe": "",
                    "long_press": ""
                }
            doc_content[act_name] = doc
            with open(doc_path, "w") as outfile:
                outfile.write(str(doc_content))
            doc_count += 1
            print_with_color(f"Documentation generated and saved to {doc_path}", "yellow")
        else:
            print_with_color(f"ERROR: Undefined decision! {decision}", "red")
            break
    else:
        print_with_color(rsp["error"]["message"], "red")
        break
    time.sleep(configs["REQUEST_INTERVAL"])

if task_complete:
    print_with_color(f"Autonomous exploration completed successfully. {doc_count} docs generated.", "yellow")
elif round_count == configs["MAX_ROUNDS"]:
    print_with_color(f"Autonomous exploration finished due to reaching max rounds. {doc_count} docs generated.",
                     "yellow")
else:
    print_with_color(f"Autonomous exploration finished unexpectedly. {doc_count} docs generated.", "red")
