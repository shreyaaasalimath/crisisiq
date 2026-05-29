import anthropic
import json, re
from dotenv import load_dotenv
load_dotenv()
client = anthropic.Anthropic()

def predict_escalation(event: dict, triage_result: dict) -> dict:
    prompt = f"""You are a disaster prediction analyst. Forecast how this situation will develop.

Event: {event['title']}
Current severity: {triage_result.get('severity')}
Event type: {triage_result.get('event_type')}
Description: {event.get('description', '')}

Respond ONLY in this JSON:
{{
  "escalation_risk": "high|medium|low",
  "predicted_severity_6h": "critical|high|medium|low",
  "predicted_severity_24h": "critical|high|medium|low",
  "key_risk_factors": ["factor1", "factor2"],
  "confidence": 85,
  "forecast_summary": "2 sentence forecast"
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
        return {"escalation_risk": "medium", "forecast_summary": raw}