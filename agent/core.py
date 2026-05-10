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

# Collect all tool definitions for Gemini
_ALL_TOOL_DEFS = []
_ALL_TOOL_DEFS.append(web_search.TOOL_DEFINITION)
_ALL_TOOL_DEFS.append(price_scraper.TOOL_DEFINITION)
_ALL_TOOL_DEFS.extend(price_tracker.TOOL_DEFINITIONS)
_ALL_TOOL_DEFS.append(price_analyzer.TOOL_DEFINITION)
_ALL_TOOL_DEFS.append(notifier.TOOL_DEFINITION)


def _build_gemini_tools():
    """Convert tool definitions to Gemini-compatible format."""
    declarations = []
    for td in _ALL_TOOL_DEFS:
        declarations.append(
            genai.protos.FunctionDeclaration(
                name=td["name"],
                description=td["description"],
                parameters=td["parameters"],
            )
        )
    return genai.protos.Tool(function_declarations=declarations)


class ShopSmartAgent:
    """AI Shopping Agent powered by Gemini with tool-use."""

    def __init__(self):
        if not config.GEMINI_API_KEY:
            raise ValueError(
                "GEMINI_API_KEY chưa được cấu hình! "
                "Hãy set biến môi trường GEMINI_API_KEY."
            )

        genai.configure(api_key=config.GEMINI_API_KEY)

        self.model = genai.GenerativeModel(
            model_name=config.GEMINI_MODEL,
            tools=[_build_gemini_tools()],
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
                    if part.function_call:
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
                if part.text:
                    final_text += part.text

            if not final_text:
                final_text = "Xin lỗi, tôi không thể xử lý yêu cầu này. Vui lòng thử lại."

            return {
                "response": final_text,
                "tool_calls": tool_calls,
                "error": None,
            }

        except Exception as e:
            traceback.print_exc()
            error_msg = str(e)

            # Handle common errors gracefully
            if "API_KEY" in error_msg.upper() or "authentication" in error_msg.lower():
                return {
                    "response": "❌ Lỗi API Key! Hãy kiểm tra lại GEMINI_API_KEY.",
                    "tool_calls": tool_calls,
                    "error": error_msg,
                }

            return {
                "response": f"❌ Đã xảy ra lỗi: {error_msg}",
                "tool_calls": tool_calls,
                "error": error_msg,
            }

    def _execute_tool(self, name: str, args: dict) -> str:
        """Execute a tool by name with given arguments."""
        fn = TOOL_FUNCTIONS.get(name)
        if not fn:
            return json.dumps({
                "success": False,
                "message": f"Tool '{name}' không tồn tại."
            })

        try:
            return fn(**args)
        except TypeError as e:
            # Handle argument mismatch
            return json.dumps({
                "success": False,
                "message": f"Lỗi tham số cho tool '{name}': {str(e)}"
            })
        except Exception as e:
            return json.dumps({
                "success": False,
                "message": f"Lỗi thực thi tool '{name}': {str(e)}"
            })
