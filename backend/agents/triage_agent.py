import anthropic
import json, re
from dotenv import load_dotenv
load_dotenv()
client = anthropic.Anthropic()

def triage(event: dict) -> dict:
    prompt = f"""You are a disaster triage specialist. Analyze this event and classify it.

Event: {event['title']}
Description: {event.get('description', '')}
Source: {event.get('source', '')}

Respond ONLY in this JSON:
{{
  "severity": "critical|high|medium|low",
  "event_type": "earthquake|flood|wildfire|hurricane|tornado|tsunami|other",
  "immediate_needs": ["need1", "need2", "need3"],
  "affected_population_estimate": "number or range",
  "assessment": "2-3 sentence expert assessment"
}}"""

    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = re.sub(r"```json|```", "", msg.content[0].text).strip()
    try:
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        return json.loads(match.group()) if match else {}
    except:
        return {"severity": "medium", "event_type": "other", "assessment": raw}