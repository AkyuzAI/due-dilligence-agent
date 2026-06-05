"""
Agent orchestrator.
Runs the research loop using OpenAI function calling,
then synthesizes all collected data into a structured report.
"""

from __future__ import annotations
import json, os
from typing import Callable, Generator
from openai import OpenAI
from dotenv import load_dotenv

from agent.tools   import TOOL_SCHEMAS, TOOL_REGISTRY
from agent.prompts import ORCHESTRATOR_SYSTEM, REPORT_SYNTHESIS_PROMPT
from agent.report  import DueDiligenceReport, report_json_schema

load_dotenv()

MODEL        = "gpt-4o"
MAX_TOOL_CALLS = {
    "quick":    6,
    "standard": 10,
    "deep":     16,
}


# ── Status callback type ──────────────────────────────────────────────────
# Passed in from Streamlit so the UI can show live progress.
StatusCallback = Callable[[str, str], None]   # (emoji, message)


class DueDiligenceAgent:

    def __init__(self, depth: str = "standard"):
        self.client     = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.max_calls  = MAX_TOOL_CALLS.get(depth, 10)
        self.research   : list[dict] = []   # raw tool results
        self.messages   : list[dict] = []   # full conversation history
        self.call_count = 0

    # ── Main entry point ──────────────────────────────────────────────────

    def run(
        self,
        company: str,
        on_status: StatusCallback | None = None,
    ) -> DueDiligenceReport:
        """
        Research a company and return a structured DueDiligenceReport.
        on_status(emoji, message) is called before each step for live UI updates.
        """
        def status(emoji: str, msg: str):
            if on_status:
                on_status(emoji, msg)

        status("🔍", f"Starting research on **{company}**...")

        # Seed the conversation
        self.messages = [
            {"role": "system", "content": ORCHESTRATOR_SYSTEM},
            {
                "role": "user",
                "content": (
                    f"Research this company thoroughly and prepare a due diligence report: {company}\n\n"
                    f"Use all available tools. Minimum 6 tool calls before synthesising. "
                    f"Always search for negative signals. "
                    f"When you have enough data, stop calling tools and I will ask you to write the report."
                ),
            },
        ]

        # ── Research loop ─────────────────────────────────────────────────
        while self.call_count < self.max_calls:
            response = self.client.chat.completions.create(
                model    = MODEL,
                messages = self.messages,
                tools    = TOOL_SCHEMAS,
                tool_choice = "auto",
            )

            msg = response.choices[0].message
            self.messages.append(msg.model_dump(exclude_none=True))

            # No more tool calls — model is done researching
            if not msg.tool_calls:
                break

            # Execute each tool call
            for tc in msg.tool_calls:
                fn_name = tc.function.name
                fn_args = json.loads(tc.function.arguments)

                tool_fn = TOOL_REGISTRY.get(fn_name)
                if not tool_fn:
                    result = f"Unknown tool: {fn_name}"
                else:
                    status(*_status_for_tool(fn_name, fn_args))
                    try:
                        result = tool_fn(**fn_args)
                    except Exception as e:
                        result = f"Tool error: {e}"

                self.research.append({
                    "tool":   fn_name,
                    "args":   fn_args,
                    "result": result,
                })

                self.messages.append({
                    "role":         "tool",
                    "tool_call_id": tc.id,
                    "content":      result[:4000],   # trim to avoid context overflow
                })

                self.call_count += 1

        status("📝", "Synthesising findings into report...")

        # ── Synthesis ─────────────────────────────────────────────────────
        research_text = _format_research(self.research)
        schema        = json.dumps(report_json_schema(), indent=2)

        synthesis_messages = [
            {"role": "system", "content": ORCHESTRATOR_SYSTEM},
            {
                "role": "user",
                "content": REPORT_SYNTHESIS_PROMPT.format(
                    schema=schema,
                    research=research_text,
                ),
            },
        ]

        synthesis = self.client.chat.completions.create(
            model       = MODEL,
            messages    = synthesis_messages,
            temperature = 0.1,    # low temp for structured output
            response_format={"type": "json_object"},
        )

        raw_json = synthesis.choices[0].message.content

        status("✅", "Report complete.")

        try:
            report = DueDiligenceReport.model_validate_json(raw_json)
        except Exception as e:
            # Fallback: try to parse and patch
            data = json.loads(raw_json)
            report = DueDiligenceReport.model_validate(data)

        return report


# ── Helpers ───────────────────────────────────────────────────────────────

def _status_for_tool(name: str, args: dict) -> tuple[str, str]:
    """Return (emoji, message) for each tool call for the status display."""
    messages = {
        "search_company_overview":      ("🏢", f"Researching company overview..."),
        "scrape_company_website":       ("🌐", f"Scraping website: {args.get('url', '')}"),
        "search_funding_financials":    ("💰", "Searching funding and financial data..."),
        "search_news":                  ("📰", "Searching recent news..."),
        "search_negative_signals":      ("⚠️",  "Checking for negative signals and controversies..."),
        "search_legal_regulatory":      ("⚖️",  "Searching legal and regulatory records..."),
        "search_employee_signals":      ("👥", "Checking employee and culture signals..."),
        "search_competitive_landscape": ("🗺️",  "Mapping competitive landscape..."),
    }
    return messages.get(name, ("🔧", f"Running {name}..."))


def _format_research(research: list[dict]) -> str:
    """Format all collected research into a readable block for synthesis."""
    parts = []
    for i, item in enumerate(research, 1):
        parts.append(
            f"=== Research Block {i}: {item['tool']} | Args: {item['args']} ===\n"
            f"{item['result']}\n"
        )
    return "\n".join(parts)
