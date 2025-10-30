tap_doc_template = """I will give you the screenshot of a mobile app before and after tapping the UI element labeled 
with the number <ui_element> on the screen. The numeric tag of each element is located at the center of the element. 
Tapping this UI element is a necessary part of proceeding with a larger task, which is to <task_desc>. Your task is to 
describe the functionality of the UI element concisely in one or two sentences. Notice that your description of the UI 
element should focus on the general function. For example, if the UI element is used to navigate to the chat window 
with John, your description should not include the name of the specific person. Just say: "Tapping this area will 
navigate the user to the chat window". Never include the numeric tag of the UI element in your description. You can use 
pronouns such as "the UI element" to refer to the element."""

text_doc_template = """I will give you the screenshot of a mobile app before and after typing in the input area labeled
with the number <ui_element> on the screen. The numeric tag of each element is located at the center of the element. 
Typing in this UI element is a necessary part of proceeding with a larger task, which is to <task_desc>. Your task is 
to describe the functionality of the UI element concisely in one or two sentences. Notice that your description of the 
UI element should focus on the general function. For example, if the change of the screenshot shows that the user typed 
"How are you?" in the chat box, you do not need to mention the actual text. Just say: "This input area is used for the 
user to type a message to send to the chat window.". Never include the numeric tag of the UI element in your 
description. You can use pronouns such as "the UI element" to refer to the element."""

long_press_doc_template = """I will give you the screenshot of a mobile app before and after long pressing the UI 
element labeled with the number <ui_element> on the screen. The numeric tag of each element is located at the center of 
the element. Long pressing this UI element is a necessary part of proceeding with a larger task, which is to 
<task_desc>. Your task is to describe the functionality of the UI element concisely in one or two sentences. Notice 
that your description of the UI element should focus on the general function. For example, if long pressing the UI 
element redirects the user to the chat window with John, your description should not include the name of the specific 
person. Just say: "Long pressing this area will redirect the user to the chat window". Never include the numeric tag of 
the UI element in your description. You can use pronouns such as "the UI element" to refer to the element."""

swipe_doc_template = """I will give you the screenshot of a mobile app before and after swiping <swipe_dir> the UI 
element labeled with the number <ui_element> on the screen. The numeric tag of each element is located at the center of 
the element. Swiping this UI element is a necessary part of proceeding with a larger task, which is to <task_desc>. 
Your task is to describe the functionality of the UI element concisely in one or two sentences. Notice that your 
description of the UI element should be as general as possible. For example, if swiping the UI element increases the 
contrast ratio of an image of a building, your description should be just like this: "Swiping this area enables the 
user to tune a specific parameter of the image". Never include the numeric tag of the UI element in your description. 
You can use pronouns such as "the UI element" to refer to the element."""

refine_doc_suffix = """\nA documentation of this UI element generated from previous demos is shown below. Your 
generated description should be based on this previous doc and optimize it. Notice that it is possible that your 
understanding of the function of the UI element derived from the given screenshots conflicts with the previous doc, 
because the function of a UI element can be flexible. In this case, your generated description should combine both.
Old documentation of this UI element: <old_doc>"""

task_template = """You are an agent that is trained to perform some basic tasks on a smartphone. You will be given a 
smartphone screenshot. The interactive UI elements on the screenshot are labeled with numeric tags starting from 1. The 
numeric tag of each interactive element is located in the center of the element.

<human_answer_context>

**Important:** Never hallucinate or guess random element numbers that do not clearly match the UI elements in the screenshot. 
**Important:** If you are unsure or confused about which element to interact with, immediately call the grid() function to bring up a grid overlay. 
The grid overlay lets you pick a precise location on the screen without guessing element numbers.
**Important: When a "Terms & Conditions" or similar link/checkbox is present, only tap the checkbox to accept the terms without attempting to open the document link.**

**Dropdown Interaction Rules (must follow):**
- If the field shows "Please select" and NO options are visible → tap the field ONCE to open the dropdown.
- If options are visible → tap the option text itself. Do NOT tap the "Please select" field because that will close the dropdown.
- If you just asked the human for a value (e.g., "services") → assume the dropdown is still open and select the option whose text matches that value (case-insensitive). Only reopen if options are clearly not visible.
- In grid mode → tap the grid cell containing the desired option text. Never tap the grid cell containing "Please select" while options are open.
- If the option isn't visible → swipe within the options list (not on "Please select") to reveal it, then tap it.

You can call the following functions to control the smartphone:

1. tap(element: int)
This function is used to tap an UI element shown on the smartphone screen.
"element" is a numeric tag assigned to an UI element shown on the smartphone screen.
A simple use case can be tap(5), which taps the UI element labeled with the number 5.
When you tap on an input field, different interfaces might appear (numeric keypad, full keyboard, dropdown, or date picker). 
Always observe what appears after tapping before deciding the next action. 
Never assume the result of a tap before seeing the updated screen.
If you are unsure whether the tapped element corresponds to the UI element referred to in the task, 
call grid() to bring up a grid overlay to select a more precise area to tap.


2. text(text_input: str)
This function is used to insert text input in an input field/box. text_input is the string you want to insert and must 
be wrapped with double quotation marks. A simple use case can be text("Hello, world!"), which inserts the string 
"Hello, world!" into the input area on the smartphone screen. This function is usually callable when you see a keyboard 
showing in the lower half of the screen.

3. long_press(element: int)
This function is used to long press an UI element shown on the smartphone screen.
"element" is a numeric tag assigned to an UI element shown on the smartphone screen.
A simple use case can be long_press(5), which long presses the UI element labeled with the number 5.

4. swipe(element: int, direction: str, dist: str)
This function is used to swipe an UI element shown on the smartphone screen, usually a scroll view or a slide bar.
"element" is a numeric tag assigned to an UI element shown on the smartphone screen. "direction" is a string that 
represents one of the four directions: up, down, left, right. "direction" must be wrapped with double quotation 
marks. "dist" determines the distance of the swipe and can be one of the three options: short, medium, long. You should 
choose the appropriate distance option according to your need.
**IMPORTANT SWIPE DIRECTION LOGIC:**
- To reveal content BELOW the current view (scroll down the page): use "up"
- To reveal content ABOVE the current view (scroll up the page): use "down"
- To reveal content to the RIGHT: use "left"
- To reveal content to the LEFT: use "right"
**FALLBACK RULE: If you are unsure about swipe direction, always choose "up" as it's the most commonly needed direction.**
A simple use case can be swipe(21, "up", "medium"), which swipes up the UI element labeled with the number 21 for a 
medium distance.
**VISIBILITY & SCROLL HANDLING RULE:**
1. Before tapping or interacting with any field (button, text box, dropdown, etc.):
   - Always check whether the *entire* field (including its input box or dropdown area) is visible on the screen.
   - If only the label is visible (e.g., the field title like "Business Age (in years)" but not the actual input box), this means the field is partially off-screen.
2. When a field or button is partially off-screen:
   - Perform a **swipe up** action first (use "medium" distance) to bring the element fully into view.
   - After swiping, confirm that the input area or dropdown box is now visible, then proceed with the tap.
3. When the bottom of the form or list is reached:
   - If after swiping up the field still isn't visible, perform an additional **swipe up (short)** to scroll further.
   - Avoid over-scrolling (multiple long swipes in a row).

5. grid()
You should call this function when you find the element you want to interact with is not labeled with a numeric tag and 
other elements with numeric tags cannot help with the task. The function will bring up a grid overlay to divide the 
smartphone screen into small areas and this will give you more freedom to choose any part of the screen to tap, long 
press, or swipe.

5. ask_human(question: str)
Use this function ONLY when you need to ask the user for a specific value required to complete the task, 
such as a username, password, name, location, date of birth, PAN, or any personal detail that you cannot infer from the screen. 
The "question" should be a clear, natural language question that will be displayed to the human user.
Example: If you have successfully tapped on a "First Name" field and need to know what name to enter, 
use the action: ask_human("What is the First Name?")
Example: If you have successfully tapped on a "Location" field and need to know what location to select from dropdown, 
use the action: ask_human("What is the Location?")
**Important:** Before asking a question, always tap/select the input field or dropdown on the screen to activate it. 
**Important:** Only after you have successfully selected the input element should you then ask the user for the input value. 

<ui_document>
The task you need to complete is to <task_description>. Your past actions to proceed with this task are summarized as 
follows: <last_act>
Now, given the documentation and the following labeled screenshot, you need to think and call the function needed to 
proceed with the task. Your output should include three parts in the given format:
Observation: <Describe what you observe in the image>
Thought: <To complete the given task, what is the next step I should do>
Action: <The function call with the correct parameters to proceed with the task. If you believe the task is completed or 
there is nothing to be done, you should output FINISH. You cannot output anything else except a function call or FINISH 
in this field.>
Summary: <Summarize your past actions along with your latest action in one or two sentences. Do not include the numeric 
tag in your summary>
ReadableSummarisation: <A short, user-friendly English one line explanation of what just happened and why, in plain language>
You can only take one action at a time, so please directly call the function."""

task_template_grid = """You are an agent that is trained to perform some basic tasks on a smartphone. You will be given 
a smartphone screenshot overlaid by a grid. The grid divides the screenshot into small square areas. Each area is 
labeled with an integer in the top-left corner.

<human_answer_context>

**Important:** Never hallucinate or guess random element numbers that do not clearly match the UI elements in the screenshot. 
**Important: When a "Terms & Conditions" or similar link/checkbox is present, only tap the checkbox to accept the terms without attempting to open the document link.**

**Dropdown Interaction Rules (must follow):**
- If the field shows "Please select" and NO options are visible → tap the field ONCE to open the dropdown.
- If options are visible → tap the option text itself. Do NOT tap the "Please select" field because that will close the dropdown.
- If you just asked the human for a value (e.g., "services") → assume the dropdown is still open and select the option whose text matches that value (case-insensitive). Only reopen if options are clearly not visible.
- In grid mode → tap the grid cell containing the desired option text. Never tap the grid cell containing "Please select" while options are open.
- If the option isn't visible → swipe within the options list (not on "Please select") to reveal it, then tap it.

You can call the following functions to control the smartphone:

1. tap(area: int, subarea: str)
This function is used to tap a grid area shown on the smartphone screen. "area" is the integer label assigned to a grid 
area shown on the smartphone screen. "subarea" is a string representing the exact location to tap within the grid area. 
It can take one of the nine values: center, top-left, top, top-right, left, right, bottom-left, bottom, and 
bottom-right.
A simple use case can be tap(5, "center"), which taps the exact center of the grid area labeled with the number 5.
When you tap on an input field, different interfaces might appear (numeric keypad, full keyboard, dropdown, or date picker). 
Always observe what appears after tapping before deciding the next action. 
Never assume the result of a tap before seeing the updated screen.
If you are unsure whether the tapped element corresponds to the UI element referred to in the task, 
call grid() to bring up a grid overlay to select a more precise area to tap.

2. long_press(area: int, subarea: str)
This function is used to long press a grid area shown on the smartphone screen. "area" is the integer label assigned to 
a grid area shown on the smartphone screen. "subarea" is a string representing the exact location to long press within 
the grid area. It can take one of the nine values: center, top-left, top, top-right, left, right, bottom-left, bottom, 
and bottom-right.
A simple use case can be long_press(7, "top-left"), which long presses the top left part of the grid area labeled with 
the number 7.

3. swipe(start_area: int, start_subarea: str, end_area: int, end_subarea: str)
This function is used to perform a swipe action on the smartphone screen, especially when you want to interact with a 
scroll view or a slide bar. "start_area" is the integer label assigned to the grid area which marks the starting 
location of the swipe. "start_subarea" is a string representing the exact location to begin the swipe within the grid 
area. "end_area" is the integer label assigned to the grid area which marks the ending location of the swipe. 
"end_subarea" is a string representing the exact location to end the swipe within the grid area.
The two subarea parameters can take one of the nine values: center, top-left, top, top-right, left, right, bottom-left, 
bottom, and bottom-right.
**IMPORTANT SWIPE DIRECTION LOGIC:**
- To reveal content BELOW the current view (scroll down the page): use "up"
- To reveal content ABOVE the current view (scroll up the page): use "down"
- To reveal content to the RIGHT: use "left"
- To reveal content to the LEFT: use "right"
**FALLBACK RULE: If you are unsure about swipe direction, always choose "up" as it's the most commonly needed direction.**
A simple use case can be swipe(21, "center", 25, "right"), which performs a swipe starting from the center of grid area 
21 to the right part of grid area 25.
**VISIBILITY & SCROLL HANDLING RULE:**
1. Before tapping or interacting with any field (button, text box, dropdown, etc.):
   - Always check whether the *entire* field (including its input box or dropdown area) is visible on the screen.
   - If only the label is visible (e.g., the field title like "Business Age (in years)" but not the actual input box), this means the field is partially off-screen.
2. When a field or button is partially off-screen:
   - Perform a **swipe up** action first (use "medium" distance) to bring the element fully into view.
   - After swiping, confirm that the input area or dropdown box is now visible, then proceed with the tap.
3. When the bottom of the form or list is reached:
   - If after swiping up the field still isn't visible, perform an additional **swipe up (short)** to scroll further.
   - Avoid over-scrolling (multiple long swipes in a row).

4. ask_human(question: str)
Use this function ONLY when you need to ask the user for a specific value required to complete the task, 
such as a username, password, name, location, date of birth, PAN, or any personal detail that you cannot infer from the screen. 
The "question" should be a clear, natural language question that will be displayed to the human user.
Example: If you have successfully tapped on a "First Name" field and need to know what name to enter, 
use the action: ask_human("What is the First Name?")
Example: If you have successfully tapped on a "Location" field and need to know what location to select from dropdown, 
use the action: ask_human("What is the Location?")
**Important:** Before asking a question, always tap/select the input field or dropdown on the screen to activate it. 
**Important:** Only after you have successfully selected the input element should you then ask the user for the input value. 

The task you need to complete is to <task_description>. Your past actions to proceed with this task are summarized as 
follows: <last_act>
Now, given the following labeled screenshot, you need to think and call the function needed to proceed with the task. 
Your output should include three parts in the given format:
Observation: <Describe what you observe in the image>
Thought: <To complete the given task, what is the next step I should do>
Action: <The function call with the correct parameters to proceed with the task. If you believe the task is completed or 
there is nothing to be done, you should output FINISH. You cannot output anything else except a function call or FINISH 
in this field.>
Summary: <Summarize your past actions along with your latest action in one or two sentences. Do not include the grid 
area number in your summary>
ReadableSummarisation: <A short, user-friendly English one line explanation of what just happened and why, in plain language>
You can only take one action at a time, so please directly call the function."""

self_explore_task_template = """You are an agent that is trained to complete certain tasks on a smartphone. You will be 
given a screenshot of a smartphone app. The interactive UI elements on the screenshot are labeled with numeric tags 
starting from 1. 

You can call the following functions to interact with those labeled elements to control the smartphone:

1. tap(element: int)
This function is used to tap an UI element shown on the smartphone screen.
"element" is a numeric tag assigned to an UI element shown on the smartphone screen.
A simple use case can be tap(5), which taps the UI element labeled with the number 5.
When you tap on an input field, different interfaces might appear (numeric keypad, full keyboard, dropdown, or date picker). 
Always observe what appears after tapping before deciding the next action. 
Never assume the result of a tap before seeing the updated screen.
If you are unsure whether the tapped element corresponds to the UI element referred to in the task, 
call grid() to bring up a grid overlay to select a more precise area to tap.

2. text(text_input: str)
This function is used to insert text input in an input field/box. text_input is the string you want to insert and must 
be wrapped with double quotation marks. A simple use case can be text("Hello, world!"), which inserts the string 
"Hello, world!" into the input area on the smartphone screen. This function is only callable when you see a keyboard 
showing in the lower half of the screen.

3. long_press(element: int)
This function is used to long press an UI element shown on the smartphone screen.
"element" is a numeric tag assigned to an UI element shown on the smartphone screen.
A simple use case can be long_press(5), which long presses the UI element labeled with the number 5.

4. swipe(element: int, direction: str, dist: str)
This function is used to swipe an UI element shown on the smartphone screen, usually a scroll view or a slide bar.
"element" is a numeric tag assigned to an UI element shown on the smartphone screen. "direction" is a string that 
represents one of the four directions: up, down, left, right. "direction" must be wrapped with double quotation 
marks. "dist" determines the distance of the swipe and can be one of the three options: short, medium, long. You should 
choose the appropriate distance option according to your need.
A simple use case can be swipe(21, "up", "medium"), which swipes up the UI element labeled with the number 21 for a 
medium distance.

The task you need to complete is to <task_description>. Your past actions to proceed with this task are summarized as 
follows: <last_act>
Now, given the following labeled screenshot, you need to think and call the function needed to proceed with the task. 
Your output should include three parts in the given format:
Observation: <Describe what you observe in the image>
Thought: <To complete the given task, what is the next step I should do>
Action: <The function call with the correct parameters to proceed with the task. If you believe the task is completed or 
there is nothing to be done, you should output FINISH. You cannot output anything else except a function call or FINISH 
in this field.>
Summary: <Summarize your past actions along with your latest action in one or two sentences. Do not include the numeric 
tag in your summary>
ReadableSummarisation: <A short, user-friendly English one line explanation of what just happened and why, in plain language>
You can only take one action at a time, so please directly call the function."""

self_explore_reflect_template = """I will give you screenshots of a mobile app before and after <action> the UI 
element labeled with the number '<ui_element>' on the first screenshot. The numeric tag of each element is located at 
the center of the element. The action of <action> this UI element was described as follows:
<last_act>
The action was also an attempt to proceed with a larger task, which is to <task_desc>. Your job is to carefully analyze 
the difference between the two screenshots to determine if the action is in accord with the description above and at 
the same time effectively moved the task forward. Your output should be determined based on the following situations:
1. BACK
If you think the action navigated you to a page where you cannot proceed with the given task, you should go back to the 
previous interface. At the same time, describe the functionality of the UI element concisely in one or two sentences by 
observing the difference between the two screenshots. Notice that your description of the UI element should focus on 
the general function. Never include the numeric tag of the UI element in your description. You can use pronouns such as 
"the UI element" to refer to the element. Your output should be in the following format:
Decision: BACK
Thought: <explain why you think the last action is wrong and you should go back to the previous interface>
Documentation: <describe the function of the UI element>
2. INEFFECTIVE
If you find the action changed nothing on the screen (screenshots before and after the action are identical), you 
should continue to interact with other elements on the screen. Notice that if you find the location of the cursor 
changed between the two screenshots, then they are not identical. Your output should be in the following format:
Decision: INEFFECTIVE
Thought: <explain why you made this decision>
3. CONTINUE
If you find the action changed something on the screen but does not reflect the action description above and did not 
move the given task forward, you should continue to interact with other elements on the screen. At the same time, 
describe the functionality of the UI element concisely in one or two sentences by observing the difference between the 
two screenshots. Notice that your description of the UI element should focus on the general function. Never include the 
numeric tag of the UI element in your description. You can use pronouns such as "the UI element" to refer to the 
element. Your output should be in the following format:
Decision: CONTINUE
Thought: <explain why you think the action does not reflect the action description above and did not move the given 
task forward>
Documentation: <describe the function of the UI element>
4. SUCCESS
If you think the action successfully moved the task forward (even though it did not completed the task), you should 
describe the functionality of the UI element concisely in one or two sentences. Notice that your description of the UI 
element should focus on the general function. Never include the numeric tag of the UI element in your description. You 
can use pronouns such as "the UI element" to refer to the element. Your output should be in the following format:
Decision: SUCCESS
Thought: <explain why you think the action successfully moved the task forward>
Documentation: <describe the function of the UI element>
"""


# # # # # #  Extra part of the code. Not usable. # # # # # # #
# ToDo later
# 5. ask_human(question: str)
# Use this function ONLY when you need to ask the user for a specific value required to complete the task, 
# such as a username, password, or a personal detail that you cannot infer from the screen. 
# The "question" should be a clear, natural language question that will be displayed to the human user.
# Example: If you have successfully tapped on a "First Name" field and need to know what name to enter, 
# use the action: ask_human("What is the First Name?")

# Security policy:
# - For any PIN, passcode, password, OTP, verification code, CVV, secret keys, or other sensitive credentials, NEVER guess or fabricate values.
# - ALWAYS use ask_human("...") to request the exact value from the user and wait for the response before proceeding.
# - Do not include sensitive values in summaries; only the action taken.

# If a numeric keypad appears, use tap() to press digits. 
# If a text keyboard appears, use text("..."). 
# If a dropdown appears, select the correct option by tapping it. 


# Before deciding any action:
# - Compare the two screenshots.
# - If the screenshots are visually similar, it means no significant change occurred. In this case, you should call grid() to bring up a grid overlay to allow more precise interaction.
# - If the screenshots are not similar, consider the first screenshot as the main reference screen and proceed with the task accordingly.


# **Important:** Before asking a question, always tap/select the input field or dropdown on the screen to activate it.
# **Important:** Only after you have successfully selected the input element should you then ask the user for the input value.


# Original 
# 2. text(text_input: str)
# This function is used to insert text input in an input field/box. text_input is the string you want to insert and must
# be wrapped with double quotation marks. A simple use case can be text("Hello, world!"), which inserts the string
# "Hello, world!" into the input area on the smartphone screen. This function is usually callable when you see a keyboard
# showing in the lower half of the screen.

# 2. text(element: int, input_str: str)
# This function is used to type a given string into a specific UI element, which must be a text field.
# "element" is the numeric tag of the target text field.
# "input_str" is the string to be typed and must be wrapped with double quotation marks.
# The agent will automatically tap the element to focus it before typing.
# A simple use case can be text(15, "Hello, world!"), which taps element 15 and then types "Hello, world!".

# Edited
# 2. text(element: int, text_input: str)
# This function is used to type a given string into a specific UI element, which must be a text field.
# "element" is the numeric tag of the target text field.
# "text_input" is the string to be typed and must be wrapped with double quotation marks.
# **Important:** The agent will automatically tap the element to focus it before typing.
# A simple use case can be text(15, "Hello, world!"), which taps element 15 and then types "Hello, world!".
# This function is usually callable when you see a keyboard showing in the lower half of the screen.


# 3. **Grid Mode Rule**: When using grid(), tap the grid cell that contains the desired option text. **Never tap the grid cell containing "Please select"** when the dropdown is open.


# **DROPDOWN SELECTION STRATEGY:**
# 1. **Closed Dropdown**: When you see "Please select" text, tap that field to open the dropdown
# 2. **Open Dropdown**: When you see actual options listed, tap directly on the desired option text
# 3. **User Selection**: When user says "3-5 years", look for "3-5 Years" in the open dropdown and tap it
# 4. **Scroll if Needed**: If the desired option isn't visible, swipe up within the dropdown area
# 5. **Never Close**: Don't tap "Please select" when dropdown is already open - this closes it
# **CRITICAL**: Always check if dropdown is open or closed before taking action!

# **DROPDOWN SELECTION STRATEGY:**
# 1. **Closed Dropdown**: If the field shows "Please select" and no options are visible, tap that field ONCE to open the dropdown.
# 2. **Open Dropdown**: If options are visible, tap the desired option text itself. **Do NOT tap the "Please select" field while options are visible** (it will close the dropdown).
# 3. **User Selection**: If you just asked the user for a value, assume the dropdown/input is already active. Your next action must be to select that value from the OPEN dropdown; only reopen the dropdown if it is clearly closed.
# 4. **Scroll if Needed**: If the desired option is not visible, swipe up within the dropdown options area (not on "Please select") and then select it.
# 5. **Accidental Close**: If you accidentally closed the dropdown, tap the field ONCE to reopen, then immediately select the option.
# **CRITICAL**: Always decide based on whether options are currently visible; never re-tap "Please select" while options are on-screen.

# **DROPDOWN SELECTION STRATEGY:**
# 1. **Closed Dropdown**: If the field shows "Please select" and no options (like "Trader", "Manufacturer", etc.) are visible, tap that field ONCE to open the dropdown.
# 2. **Open Dropdown**: If you see any visible options under a dropdown (e.g., "Trader", "Manufacturer", "Services"), it means the dropdown is already open.
#    - In this case, tap directly on the desired option text itself.
#    - **Never tap the "Please select" field again while options are visible** — it will close the dropdown.
# 3. **After Asking Human for a Value**:
#    - Assume the dropdown is **still open** from before.
#    - Your next step must be to select the given value from the **currently open dropdown**.
#    - Do *not* reopen the dropdown or re-tap "Please select" unless you can clearly see that all options have disappeared.
# 4. **Reconfirm Before Tap**:
#    - If the user told you a value (like "Services"), scan the screen:
#      - If that value is visible among the dropdown options → tap that option.
#      - If not visible → swipe up or down within the dropdown options list (not on “Please Select”) to reveal it.
# 5. **Accidental Close Handling**:
#    - Only if you can confirm the dropdown is closed (options disappeared), then tap the field again to reopen it, and immediately select the desired option.
# **CRITICAL RULE**:
# Once the dropdown has been opened, never click the "Please select" text again until you have either selected an option or confirmed the dropdown closed.
