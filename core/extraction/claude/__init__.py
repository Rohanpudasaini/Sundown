import json

from core.extraction import BaseExtraction, EXTRACTION_SYSTEM_PROMPT
from anthropic import Anthropic
from config import settings


class ClaudeExtraction(BaseExtraction):
    def __init__(self):
        if not settings.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY must be set in environment variables")
        self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    def extract(
        self, entry_text: str, prior_extractions: list[dict] | None = None
    ) -> dict:
        system_prompt = EXTRACTION_SYSTEM_PROMPT
        if prior_extractions:
            system_prompt += "\n\nPrior Extractions:\n" + "\n".join(
                f"- {e.get('extracted_at')}: mood={e.get('mood')}, topics={e.get('topics')}, wins={e.get('wins')}, missed={e.get('missed')}, intentions={e.get('intentions')}, recurring_themes={e.get('recurring_themes')}"
                for e in prior_extractions[-7:]
            )
            print("*" * 50)
            print(f"Using prior extractions for context: {prior_extractions[-7:]}")
            print(f"System prompt with prior extractions: {system_prompt}")
            print("*" * 50)

        response = self.client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=500,
            system=system_prompt,
            temperature=0.0,
            messages=[
                {"role": "user", "content": entry_text},
            ],
        )
        block = response.content[0]
        if block.type != "text":
            raise ValueError(
                f"Unexpected response format from Claude got block type {block.type}, expected 'text'"
            )
        text = (
            block.text.strip()
            .removeprefix("```json")
            .removeprefix("```")
            .removesuffix("```")
            .strip()
        )

        ## Pharsing with regex if the above doesn't work reliably

        # import re

        # text = block.text.strip()
        # # Remove ```json ... ``` or ``` ... ```
        # text = re.sub(r"^```(?:json)?\s*", "", text)
        # text = re.sub(r"\s*```$", "", text)

        return json.loads(text)
