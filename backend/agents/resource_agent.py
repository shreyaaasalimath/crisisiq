import anthropic
import json, re
from dotenv import load_dotenv
load_dotenv()
client = anthropic.Anthropic()

def match_resources(event: dict, triage_result: dict, available_resources: list) -> dict:
    resources_str = "\n".join([
        f"- {r['name']} ({r['resource_type']}): {r['available']} units available, {r['distance_km']:.1f}km away"
        for r in available_resources[:6]
    ])

    prompt = f"""You are a disaster resource coordinator. Match resources to this emergency.

Event: {event['title']}
Severity: {triage_result.get('severity', 'unknown')}
Immediate needs: {triage_result.get('immediate_needs', [])}

Available resources nearby:
{resources_str}

Respond ONLY in this JSON:
{{
  "recommended_resources": ["resource name 1", "resource name 2"],
  "resource_gap": "what is still missing",
  "priority_action": "single most important action to take right now",
  "estimated_response_time": "X hours"
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
        return {"priority_action": raw}