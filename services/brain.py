"""Autonomous ReAct Reasoning Loop with streaming tokens and tool execution."""

import json
from typing import AsyncGenerator, Optional
from groq import AsyncGroq
from core.config import GROQ_API_KEY, GROQ_LLM_MODEL
from core.state import ConversationState
from tools import TOOL_SCHEMAS, dispatch_tool

class AgentBrain:
    """
    Pure Python asynchronous ReAct (Reason + Act) loop.
    1. Sends conversation history + JSON schemas to Groq LLM.
    2. Resolves and executes tool calls recursively.
    3. Streams the final conversational response tokens for sub-500ms TTFA synthesis.
    """

    def __init__(self, api_key: str = GROQ_API_KEY, model: str = GROQ_LLM_MODEL):
        self.api_key = api_key
        self.model = model
        self.client = AsyncGroq(api_key=self.api_key)

    async def execute_react_turn(
        self,
        state: ConversationState,
        max_tool_iterations: int = 5
    ) -> AsyncGenerator[str, None]:
        """
        Executes ReAct iterations until all tool calls are resolved,
        then yields response tokens incrementally.
        """
        iterations = 0

        while iterations < max_tool_iterations:
            iterations += 1
            messages = state.get_messages()

            # Non-streaming check first to see if model desires tool execution
            completion = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=TOOL_SCHEMAS,
                tool_choice="auto",
                temperature=0.3,
            )

            response_msg = completion.choices[0].message
            tool_calls = response_msg.tool_calls

            if tool_calls:
                # Model requested tool calls
                for tc in tool_calls:
                    fn_name = tc.function.name
                    fn_args = tc.function.arguments
                    tool_call_id = tc.id

                    state.add_tool_call(tool_call_id, fn_name, fn_args)
                    result_str = dispatch_tool(fn_name, fn_args)
                    state.add_tool_result(tool_call_id, fn_name, result_str)

                # Loop again to let the LLM evaluate tool results
                continue
            else:
                # No more tools needed; stream final response tokens
                break

        # Stream the conversational answer tokens
        messages = state.get_messages()
        stream_response = await self.client.chat.completions.create(
            model=self.model,
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

        # Record completed assistant output in conversational state
        completed_text = "".join(full_content).strip()
        if completed_text:
            state.add_assistant_message(completed_text)
