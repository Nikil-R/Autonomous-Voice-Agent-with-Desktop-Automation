"""Autonomous ReAct Reasoning Loop with streaming tokens and tool execution."""

import json
from typing import AsyncGenerator, Optional
from groq import AsyncGroq, RateLimitError, APIError
from core.config import GROQ_API_KEY, GROQ_LLM_MODEL, GROQ_FALLBACK_MODELS, GEMINI_API_KEY
from core.state import ConversationState
from tools import TOOL_SCHEMAS, dispatch_tool

class AgentBrain:
    """
    Pure Python asynchronous ReAct (Reason + Act) loop.
    1. Sends conversation history + JSON schemas to high-speed LLMs (openai/gpt-oss-20b, 120b, qwen).
    2. Automatically cascades through fallback models upon encountering any 429 rate limit.
    3. Seamlessly falls back to Google Gemini 3.5 Flash if needed.
    4. Resolves and executes tool calls recursively.
    5. Streams the final conversational response tokens for sub-500ms TTFA synthesis.
    """

    def __init__(self, api_key: str = GROQ_API_KEY, model: str = GROQ_LLM_MODEL):
        self.api_key = api_key
        self.model = model
        self.fallback_models = GROQ_FALLBACK_MODELS
        self.client = AsyncGroq(api_key=self.api_key) if self.api_key else None
        self.gemini_api_key = GEMINI_API_KEY

    async def _gemini_fallback(self, state: ConversationState) -> AsyncGenerator[str, None]:
        """Direct fallback generation using Google Gemini when all Groq models hit rate limits."""
        try:
            from google import genai
            client = genai.Client(api_key=self.gemini_api_key)
            messages = state.get_messages()
            prompt_parts = []
            for m in messages:
                role = m.get("role", "user")
                content = m.get("content", "")
                if role == "system":
                    prompt_parts.append(f"System instruction: {content}")
                elif role == "user":
                    prompt_parts.append(f"User: {content}")
                elif role == "assistant":
                    prompt_parts.append(f"Assistant: {content}")
            full_prompt = "\n\n".join(prompt_parts) + "\n\nAssistant (concise, direct conversational response without markdown asterisks):"

            res = None
            for model_name in ["gemini-3.5-flash", "gemini-3.8-flash"]:
                try:
                    res = client.models.generate_content(
                        model=model_name,
                        contents=full_prompt
                    )
                    if res and res.text:
                        break
                except Exception:
                    continue
            reply = res.text.strip() if (res and res.text) else "I am here and ready to help."
            reply = reply.replace("**", "").replace("*", "")
            state.add_assistant_message(reply)
            yield reply
        except Exception as e:
            fallback_err = f"I am ready to help, but encountered a temporary connection issue."
            state.add_assistant_message(fallback_err)
            yield fallback_err

    async def execute_react_turn(
        self,
        state: ConversationState,
        max_tool_iterations: int = 5
    ) -> AsyncGenerator[str, None]:
        """
        Executes ReAct iterations until all tool calls are resolved,
        then yields response tokens incrementally.
        Cascades through candidate models if rate limited.
        """
        models_to_try = [self.model] + [m for m in self.fallback_models if m != self.model]
        
        for candidate_model in models_to_try:
            try:
                iterations = 0
                while iterations < max_tool_iterations:
                    iterations += 1
                    messages = state.get_messages()

                    completion = await self.client.chat.completions.create(
                        model=candidate_model,
                        messages=messages,
                        tools=TOOL_SCHEMAS,
                        tool_choice="auto",
                        temperature=0.3,
                    )

                    response_msg = completion.choices[0].message
                    tool_calls = response_msg.tool_calls

                    if tool_calls:
                        action_spoken_messages = []
                        for tc in tool_calls:
                            fn_name = tc.function.name
                            fn_args = tc.function.arguments
                            tool_call_id = tc.id

                            state.add_tool_call(tool_call_id, fn_name, fn_args)
                            result_str = dispatch_tool(fn_name, fn_args)
                            state.add_tool_result(tool_call_id, fn_name, result_str)

                            try:
                                res_obj = json.loads(result_str)
                                if isinstance(res_obj, dict) and "message" in res_obj:
                                    action_spoken_messages.append(res_obj["message"])
                            except Exception:
                                pass

                        action_tools = {
                            "open_url",
                            "open_application",
                            "control_media_or_volume",
                            "search_web_or_play",
                            "open_folder_or_path",
                            "desktop_type_or_calculate",
                            "focus_window",
                            "control_chrome_tab_video",
                            "click_chrome_element",
                            "fill_chrome_search",
                            "click_on_visual_target",
                            "capture_and_analyze_screen"
                        }
                        executed_tool_names = {tc.function.name for tc in tool_calls}
                        if action_spoken_messages and executed_tool_names.issubset(action_tools):
                            immediate_reply = " ".join(action_spoken_messages)
                            state.add_assistant_message(immediate_reply)
                            yield immediate_reply
                            return

                        continue
                    else:
                        break

                # Stream final response tokens
                messages = state.get_messages()
                stream_response = await self.client.chat.completions.create(
                    model=candidate_model,
                    messages=messages,
                    stream=True,
                    temperature=0.3,
                )

                full_content = []
                async for chunk in stream_response:
                    delta = chunk.choices[0].delta.content or ""
                    if delta:
                        full_content.append(delta)
                        yield delta

                completed_text = "".join(full_content).strip()
                if completed_text:
                    state.add_assistant_message(completed_text)
                return

            except (RateLimitError, APIError) as e:
                print(f"[AgentBrain] Rate limit or API error on model {candidate_model}: {e}. Trying next fallback...")
                continue
            except Exception as e:
                print(f"[AgentBrain] Unexpected error on model {candidate_model}: {e}. Trying next fallback...")
                continue

        # If all Groq models exhausted, use Gemini fallback
        print("[AgentBrain] All Groq models exhausted; switching to Gemini...")
        async for token in self._gemini_fallback(state):
            yield token


