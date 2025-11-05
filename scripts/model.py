import re
from abc import abstractmethod
from typing import List
from http import HTTPStatus
import sys
import time
import requests
import dashscope
try:
    import google.generativeai as genai
    GEMINI_SDK_AVAILABLE = True
except ImportError:
    GEMINI_SDK_AVAILABLE = False

from utils import encode_image, speak

from config import load_config
configs = load_config()

from logging_controller import get_logger
try:
    logger = get_logger()
except Exception as e:
    print(f"ERROR: Failed to load logger configuration: {e}")
    sys.exit(1)

class BaseModel:
    def __init__(self):
        pass

    @abstractmethod
    def get_model_response(self, prompt: str, images: List[str]) -> (bool, str):
        pass


class OpenAIModel(BaseModel):
    def __init__(self, base_url: str, api_key: str, model: str, temperature: float, max_completion_tokens: int):
        super().__init__()
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_completion_tokens = max_completion_tokens
    def get_model_response(self, prompt: str, images: List[str]) -> (bool, str):
        content = [
            {
                "type": "text",
                "text": prompt
            }
        ]
        for img in images:
            base64_img = encode_image(img)
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_img}"
                }
            })
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": content
                }
            ],
            "temperature": self.temperature,
            "max_completion_tokens": self.max_completion_tokens
        }
        response = requests.post(self.base_url, headers=headers, json=payload).json()
        if "error" not in response:
            usage = response["usage"]
            prompt_tokens = usage["prompt_tokens"]
            completion_tokens = usage["completion_tokens"]
            logger.debug(f"Request cost is "
                             f"${'{0:.2f}'.format(prompt_tokens / 1000 * 0.01 + completion_tokens / 1000 * 0.03)}")
        else:
            return False, response["error"]["message"]
        return True, response["choices"][0]["message"]["content"]


class GeminiModel(BaseModel):
    def __init__(self, api_base: str, api_key: str, model: str, temperature: float, max_completion_tokens: int):
        super().__init__()
        self.api_base = api_base.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.temperature = float(temperature)
        self.max_completion_tokens = int(max_completion_tokens)
        self.chat_session = None
        if configs.get("ENABLE_PERSISTENT_CHAT_WITH_GEMINI_CHAT", False):
            self._initialize_chat()

    def _initialize_chat(self):
        """Initialize Gemini chat session - it handles history automatically"""
        if not GEMINI_SDK_AVAILABLE:
            logger.warning("Gemini SDK not available. Using REST API without persistence.")
            return
            
        try:
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel(self.model)
            # Start chat - Gemini stores the history automatically
            self.chat_session = model.start_chat()
            
            logger.info(f"Gemini chat session started - history managed by Gemini")
            
        except Exception as e:
            logger.error(f"Failed to start Gemini chat: {e}")
    def get_model_response(self, prompt: str, images: List[str]) -> (bool, str):
        if self.chat_session:
            try:
                print("Using Gemini Chat Persistent session with history.")
                return self._chat_response(prompt, images)
            except Exception as e:
                logger.error(f"Gemini Chat response failed: {e}")
                return self.actual_model_response(prompt, images)
        else:
            print("Using Gemini session without history.")
            return self.actual_model_response(prompt, images)
    def _chat_response(self, prompt: str, images: List[str]) -> (bool, str):
        """Use Gemini chat session - history is automatic"""
        try:
            # Prepare content
            content = [prompt]
            for img in images:
                from PIL import Image
                pil_image = Image.open(img)
                content.append(pil_image)
            
            # Send to chat session - Gemini automatically includes history
            start_time = time.perf_counter()
            response = self.chat_session.send_message(
                content,
                generation_config=genai.types.GenerationConfig(
                    temperature=self.temperature,
                    max_output_tokens=self.max_completion_tokens
                )
            )
            end_time = time.perf_counter()
            delay_seconds = end_time - start_time
            print(f"Gemini Chat Request Time (seconds): {delay_seconds:.4f}")
            print(f"Gemini Chat Request Time (milliseconds): {delay_seconds * 1000:.2f} ms")
        
            # Gemini automatically tracks history, you can check it:
            logger.debug(f"Chat history length: {len(self.chat_session.history)}")
            return True, response.text
        except Exception as e:
            logger.error(f"Gemini chat failed: {e}")
            return False, str(e)
        
    def actual_model_response(self, prompt: str, images: List[str]) -> (bool, str):
        # Build parts: text + inline images
        parts = [{"text": prompt}]
        for img in images:
            base64_img = encode_image(img)
            parts.append({
                "inline_data": {
                    "mime_type": "image/jpeg",
                    "data": base64_img
                }
            })

        url = f"{self.api_base}/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": parts
                }
            ],
            "generationConfig": {
                "temperature": self.temperature,
                "maxOutputTokens": self.max_completion_tokens
            }
        }

        try:
            start_time = time.perf_counter()
            response = requests.post(url, json=payload, timeout=120)
            end_time = time.perf_counter()
            delay_seconds = end_time - start_time
            print(f"Gemini Request Time (seconds): {delay_seconds:.4f}")
            print(f"Gemini Request Time (milliseconds): {delay_seconds * 1000:.2f} ms")
            data = response.json()
           # print(f"data: {data}")
        except Exception as e:
            return False, f"Request failed: {e}"

        # Error handling
        if "error" in data:
            return False, data["error"].get("message", "Unknown Gemini API error")

        candidates = data.get("candidates", [])
        if not candidates:
            return False, "No candidates returned by Gemini"

        # Extract text from first candidate
        parts_out = candidates[0].get("content", {}).get("parts", [])
        text = "".join(p.get("text", "") for p in parts_out)

        # Optional token usage logging (no pricing printed)
        usage = data.get("usageMetadata")
        if usage:
            prompt_tokens = usage.get("promptTokenCount", 0)
            completion_tokens = usage.get("candidatesTokenCount", 0)
            total_tokens = usage.get("totalTokenCount", 0)
            # logger.debug(f"Token usage (Gemini) - prompt: {prompt_tokens}, completion: {completion_tokens}, total: {total_tokens}")

        return True, text if text else "``(No text in Gemini response)``"
    def get_chat_history(self):
        """Get the chat history from Gemini's session"""
        if self.chat_session:
            return self.chat_session.history
        return []

    def clear_session(self):
        """Start fresh session"""
        if GEMINI_SDK_AVAILABLE:
            self._initialize_chat()
            logger.info("Chat session cleared - new session started")

def parse_explore_rsp(rsp):
    try:
        observation = re.findall(r"Observation: (.*?)$", rsp, re.MULTILINE)[0]
        think = re.findall(r"Thought: (.*?)$", rsp, re.MULTILINE)[0]
        act = re.findall(r"Action: (.*?)$", rsp, re.MULTILINE)[0]
        last_act = re.findall(r"Summary: (.*?)$", rsp, re.MULTILINE)[0]
        readable = re.findall(r"ReadableSummarisation: (.*?)$", rsp, re.MULTILINE)[0]

        logger.debug(f"Observation: => {observation}")
        logger.debug(f"Thought: => {think}")
        logger.info(f"Action: => {act}")
        logger.debug(f"Summary: => {last_act}")
        logger.debug(f"ReadableSummarisation: => {readable}")

        if configs.get("ENABLE_VOICE", False):
            speak(readable)
        if "FINISH" in act:
            return ["FINISH"]
        act_name = act.split("(")[0]
        if act_name == "tap":
            area = int(re.findall(r"tap\((.*?)\)", act)[0])
            return [act_name, area, last_act]
        elif act_name == "text":
            input_str = re.findall(r"text\((.*?)\)", act)[0][1:-1]
            return [act_name, input_str, last_act]
        elif act_name == "long_press":
            area = int(re.findall(r"long_press\((.*?)\)", act)[0])
            return [act_name, area, last_act]
        elif act_name == "swipe":
            params = re.findall(r"swipe\((.*?)\)", act)[0]
            area, swipe_dir, dist = params.split(",")
            area = int(area)
            swipe_dir = swipe_dir.strip()[1:-1]
            dist = dist.strip()[1:-1]
            return [act_name, area, swipe_dir, dist, last_act]
        elif act_name == "grid":
            return [act_name]
        elif act_name == "ask_human":
            # Extracts the question from ask_human("Some question?")
            question = re.findall(r'ask_human\("(.*?)"\)', act)[0]
            return [act_name, question, last_act]
        else:
            logger.error(f"ERROR: Undefined act {act_name}!")
            return ["ERROR"]
    except Exception as e:
        logger.error(f"ERROR: an exception occurs while parsing the model response in parse_explore_rsp: {e}")
        logger.error(rsp)
        return ["ERROR"]


def parse_grid_rsp(rsp):
    try:
        # observation = re.findall(r"Observation: (.*?)$", rsp, re.MULTILINE)[0]
        # think = re.findall(r"Thought: (.*?)$", rsp, re.MULTILINE)[0]
        act = re.findall(r"Action: (.*?)$", rsp, re.MULTILINE)[0]
        last_act = re.findall(r"Summary: (.*?)$", rsp, re.MULTILINE)[0]
        readable = re.findall(r"ReadableSummarisation: (.*?)$", rsp, re.MULTILINE)[0]
        # logger.debug(f"Observation: => {observation}")
        # logger.debug(f"Thought: => {think}")
        logger.info(f"Action: => {act}")
        # logger.debug(f"Summary: => {last_act}")
        logger.debug(f"ReadableSummarisation: => {readable}")
        # readable = last_act
        if configs.get("ENABLE_VOICE", False):
            speak(readable)
        if "FINISH" in act:
            return ["FINISH"]
        act_name = act.split("(")[0]
        if act_name == "tap":
            params = re.findall(r"tap\((.*?)\)", act)[0].split(",")
            area = int(params[0].strip())
            subarea = params[1].strip()[1:-1]
            return [act_name + "_grid", area, subarea, last_act]
        elif act_name == "text":
            input_str = re.findall(r"text\((.*?)\)", act)[0][1:-1]
            return [act_name, input_str, last_act]
        elif act_name == "long_press":
            params = re.findall(r"long_press\((.*?)\)", act)[0].split(",")
            area = int(params[0].strip())
            subarea = params[1].strip()[1:-1]
            return [act_name + "_grid", area, subarea, last_act]
        elif act_name == "swipe":
            params = re.findall(r"swipe\((.*?)\)", act)[0].split(",")
            start_area = int(params[0].strip())
            start_subarea = params[1].strip()[1:-1]
            end_area = int(params[2].strip())
            end_subarea = params[3].strip()[1:-1]
            return [act_name + "_grid", start_area, start_subarea, end_area, end_subarea, last_act]
        elif act_name == "grid":
            return [act_name]
        elif act_name == "ask_human":
            # Extracts the question from ask_human("Some question?")
            question = re.findall(r'ask_human\("(.*?)"\)', act)[0]
            return [act_name, question, last_act]
        else:
            logger.error(f"ERROR: Undefined act {act_name}!")
            return ["ERROR"]
    except Exception as e:
        logger.error(f"ERROR: an exception occurs while parsing the model response in parse_grid_rsp: {e}")
        logger.error(rsp)
        return ["ERROR"]


def parse_reflect_rsp(rsp):
    try:
        decision = re.findall(r"Decision: (.*?)$", rsp, re.MULTILINE)[0]
        think = re.findall(r"Thought: (.*?)$", rsp, re.MULTILINE)[0]
        logger.debug(f"Decision: {decision}")
        logger.debug(f"Thought: {think}")
        if decision == "INEFFECTIVE":
            return [decision, think]
        elif decision == "BACK" or decision == "CONTINUE" or decision == "SUCCESS":
            doc = re.findall(r"Documentation: (.*?)$", rsp, re.MULTILINE)[0]
            logger.debug(f"Documentation: {doc}")
            return [decision, think, doc]
        else:
            logger.error(f"ERROR: Undefined decision {decision}!")
            return ["ERROR"]
    except Exception as e:
        logger.error(f"ERROR: an exception occurs while parsing the model response in parse_reflect_rsp: {e}")
        logger.error(rsp)
        return ["ERROR"]
