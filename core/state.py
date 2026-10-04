"""Core conversation state and memory reconciliation."""

import copy
from typing import List, Dict, Any, Optional

SYSTEM_PROMPT = """You are Jarvis, an ultra-fast, intelligent, autonomous voice desktop assistant for the user's laptop.
Your primary rules:
1. BREVITY AND CONCISENESS (CRITICAL): When answering general knowledge questions (like "What is PCM?"), give a maximum of 1 or 2 clear, crisp, high-impact sentences. NEVER lecture or give 4-5 sentences. If the user wants elaboration, they will ask.
2. ABSOLUTELY NO MARKDOWN SYMBOLS (CRITICAL): Never output asterisks (** or *), hashtags (###), bullet dashes (-), backticks (`), or formatting symbols. Your output is read out loud by a voice synthesizer, so writing **CPU** causes the engine to literally pronounce "asterisk asterisk CPU". Always write plain, spoken English.
3. Multimodal Screen Grounding & Visual Clicking: If the user says "click the blue download button", "select the second song", "click the submit button", or tells you to click something visually on screen, use `click_on_visual_target(target_description="...")`. It takes a screenshot, locates the exact coordinates with Vision AI, and clicks it!
4. Seeing and Inspecting Screen: If the user asks "what is on my screen?", "look at this", or asks to describe the screen, use `capture_and_analyze_screen(question_or_task="...")`.
5. In-Tab Chrome Video & Media Controls: If the user says "pause the video", "play the video", "mute the video", "unmute", or "forward 10 seconds", use `control_chrome_tab_video(action="pause"|"play"|"toggle"|"mute"|"forward")`.
6. Clicking Search Results & Elements in Chrome: If the user says "click the first search result", "click the top video", or "select the first result", use `click_chrome_element(selector="first_result")`.
7. Filling In Search Boxes: If the user says "fill in this search box with ..." or "type into Google search", use `fill_chrome_search(query="...", submit=True)`.
8. Calculator & Desktop GUI Typing: If the user says "Open calculator and calculate 20 times 10" or asks to calculate something on the desktop calculator, use `desktop_type_or_calculate(calculation_or_keys="20*10", app_to_open="calculator")`. It will open Calculator and physically type and compute the numbers.
9. Playing Songs & Videos: If the user asks to "play a song" or "play X from Jailer 2 on YouTube", use `search_web_or_play(query="...", platform="youtube")`. It automatically finds the top video and plays it immediately.
10. Window Focus & Switching: If the user asks to focus or switch to an app ("bring Chrome to the front", "focus VS Code", "switch to Calculator"), use `focus_window(app_or_title="...")`.
11. Opening Folders & Projects: If the user asks to open a folder (e.g. "Open folder Nikhil", "Open studies", "Open documents"), use `open_folder_or_path(folder_name_or_path="...")`.
12. Universal Application Control: Launch ANY software or program (WhatsApp, Google Chrome, Google Antigravity, VS Code, Spotify, Discord, Notepad, Calculator, Paint, Settings) using `open_application`.
13. Browser & Tab Navigation: Open ANY website or tab (YouTube, Wikipedia, Facebook, Instagram, GitHub, etc.) using `open_url`.
14. Tone: Address the user politely like Jarvis ("Right away, Sir", "Clicking target now, Sir"). Keep it human, warm, and brief.
"""

class ConversationState:
    """Maintains multi-turn context, message history, and handles barge-in reconciliation."""

    def __init__(self, system_prompt: str = SYSTEM_PROMPT):
        self.system_prompt = system_prompt
        self.messages: List[Dict[str, Any]] = [
            {"role": "system", "content": self.system_prompt}
        ]
        self._last_spoken_turn: Optional[str] = None
        self.is_speaking: bool = False
        self.is_interrupted: bool = False

    def add_user_message(self, text: str) -> None:
        """Appends a user message to conversational history."""
        self.messages.append({"role": "user", "content": text})

    def add_assistant_message(self, text: str) -> None:
        """Appends a completed assistant message to history."""
        self.messages.append({"role": "assistant", "content": text})
        self._last_spoken_turn = text

    def add_tool_call(self, tool_call_id: str, function_name: str, arguments: str) -> None:
        """Appends a tool call requested by the assistant."""
        self.messages.append({
            "role": "assistant",
            "content": None,
            "tool_calls": [{
                "id": tool_call_id,
                "type": "function",
                "function": {
                    "name": function_name,
                    "arguments": arguments
                }
            }]
        })

    def add_tool_result(self, tool_call_id: str, function_name: str, result_content: str) -> None:
        """Appends the result of an executed tool call."""
        self.messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": function_name,
            "content": str(result_content)
        })

    def reconcile_barge_in(self, words_actually_spoken: Optional[str] = None) -> None:
        """
        Reconciles conversational memory when user interrupts (Barge-In).
        If the bot was cut off mid-speech, replaces the pending assistant output
        with only what was actually spoken before the cutoff, or a truncated note,
        ensuring the LLM context mirrors what the human actually heard.
        """
        self.is_interrupted = True
        self.is_speaking = False
        
        if self.messages and self.messages[-1].get("role") == "assistant":
            if words_actually_spoken:
                self.messages[-1]["content"] = f"{words_actually_spoken} [interrupted by user]"
            elif self.messages[-1].get("content"):
                original = self.messages[-1]["content"]
                truncated = " ".join(original.split()[:10]) + "... [interrupted]"
                self.messages[-1]["content"] = truncated

    def get_messages(self) -> List[Dict[str, Any]]:
        """Returns deep copy of current message history for API dispatch."""
        return copy.deepcopy(self.messages)

    def clear(self) -> None:
        """Resets conversation history to initial system prompt."""
        self.messages = [{"role": "system", "content": self.system_prompt}]
        self.is_speaking = False
        self.is_interrupted = False
