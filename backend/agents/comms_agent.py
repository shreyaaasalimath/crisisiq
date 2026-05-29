import anthropic
import json, re
from dotenv import load_dotenv
load_dotenv()
client = anthropic.Anthropic()

def draft_alert(event: dict, triage_result: dict, resource_result: dict) -> dict:
    prompt = f"""You are an emergency communications officer. Draft an official alert.

Event: {event['title']}
Severity: {triage_result.get('severity')}
Assessment: {triage_result.get('assessment')}
Priority action: {resource_result.get('priority_action')}

Respond ONLY in this JSON:
{{
  "public_alert": "Short public-facing alert message (max 280 chars)",
  "agency_alert": "Detailed alert for emergency agencies (max 500 chars)",
  "urgency_level": "immediate|urgent|advisory|watch",
  "recommended_actions": ["action1", "action2", "action3"]
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
        return {"public_alert": raw}