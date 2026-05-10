"""
ShopSmart AI Agent Core — ReAct loop with Gemini Function Calling.
"""
import json
import traceback

import google.generativeai as genai

import config
from agent.prompts import SYSTEM_PROMPT
from agent.tools import web_search, price_scraper, price_tracker, price_analyzer, notifier


# ── Tool Registry ──────────────────────────────────────────
TOOL_FUNCTIONS = {
    "search_product": web_search.search_product,
    "scrape_price": price_scraper.scrape_price,
    "track_price": price_tracker.track_price,
    "get_tracked_products": price_tracker.get_tracked_products,
    "analyze_price": price_analyzer.analyze_price,
    "send_notification": notifier.send_notification,
}

# Pass callables directly — Gemini SDK auto-generates schema from type hints
_TOOL_CALLABLES = list(TOOL_FUNCTIONS.values())


class ShopSmartAgent:
    """AI Shopping Agent powered by Gemini with tool-use."""

    def __init__(self):
        if not config.GEMINI_API_KEY:
            raise ValueError(
                "GEMINI_API_KEY not configured! "
                "Set environment variable GEMINI_API_KEY."
            )

        genai.configure(api_key=config.GEMINI_API_KEY)

        self.model = genai.GenerativeModel(
            model_name=config.GEMINI_MODEL,
            tools=_TOOL_CALLABLES,
            system_instruction=SYSTEM_PROMPT,
        )
        self.chat = self.model.start_chat()
        print("[OK] ShopSmart Agent initialized successfully.")

    def reset_chat(self):
        """Reset the chat session."""
        self.chat = self.model.start_chat()

    def process_message(self, user_message: str) -> dict:
        """
        Process a user message through the ReAct loop.

        Returns:
            dict with keys: response (str), tool_calls (list), error (str|None)
        """
        tool_calls = []

        try:
            response = self.chat.send_message(user_message)

            # ReAct loop — keep processing until we get a text response
            iterations = 0
            while iterations < config.MAX_AGENT_ITERATIONS:
                iterations += 1

                # Check if response has function calls
                has_function_call = False
                function_responses = []

                for part in response.parts:
                    if hasattr(part, 'function_call') and part.function_call.name:
                        has_function_call = True
                        fc = part.function_call
                        fn_name = fc.name
                        fn_args = dict(fc.args) if fc.args else {}

                        print(f"  [TOOL] {fn_name}({fn_args})")

                        # Execute the tool
                        tool_result = self._execute_tool(fn_name, fn_args)

                        tool_calls.append({
                            "tool": fn_name,
                            "args": fn_args,
                            "result_preview": tool_result[:200] + "..."
                                              if len(tool_result) > 200 else tool_result,
                        })

                        function_responses.append(
                            genai.protos.Part(
                                function_response=genai.protos.FunctionResponse(
                                    name=fn_name,
                                    response={"result": tool_result},
                                )
                            )
                        )

                if not has_function_call:
                    break

                # Send all function responses back to Gemini
                response = self.chat.send_message(
                    genai.protos.Content(parts=function_responses)
                )

            # Extract final text response
            final_text = ""
            for part in response.parts:
                if hasattr(part, 'text') and part.text:
                    final_text += part.text

            if not final_text:
                final_text = "Xin loi, toi khong the xu ly yeu cau nay. Vui long thu lai."

            return {
                "response": final_text,
                "tool_calls": tool_calls,
                "error": None,
            }

        except Exception as e:
            traceback.print_exc()
            error_msg = str(e)

            if "API_KEY" in error_msg.upper() or "authentication" in error_msg.lower():
                return {
                    "response": "Loi API Key! Hay kiem tra lai GEMINI_API_KEY.",
                    "tool_calls": tool_calls,
                    "error": error_msg,
                }

            if "quota" in error_msg.lower() or "429" in error_msg:
                return {
                    "response": "API da het quota. Vui long doi vai phut hoac tao API key moi tai https://aistudio.google.com/apikey",
                    "tool_calls": tool_calls,
                    "error": error_msg,
                }

            return {
                "response": f"Da xay ra loi: {error_msg}",
                "tool_calls": tool_calls,
                "error": error_msg,
            }

    def _execute_tool(self, name: str, args: dict) -> str:
        """Execute a tool by name with given arguments."""
        fn = TOOL_FUNCTIONS.get(name)
        if not fn:
            return json.dumps({
                "success": False,
                "message": f"Tool '{name}' does not exist."
            })

        try:
            return fn(**args)
        except TypeError as e:
            return json.dumps({
                "success": False,
                "message": f"Argument error for tool '{name}': {str(e)}"
            })
        except Exception as e:
            return json.dumps({
                "success": False,
                "message": f"Error executing tool '{name}': {str(e)}"
            })
