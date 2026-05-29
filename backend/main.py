from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import json, math
from datetime import datetime

from models import init_db, get_db, DisasterEvent, Resource
from fetcher import fetch_earthquakes, fetch_weather_alerts, fetch_news_disasters
from agents.triage_agent import triage
from agents.resource_agent import match_resources
from agents.comms_agent import draft_alert
from agents.predict_agent import predict_escalation

app = FastAPI(title="CrisisIQ API")

app.add_middleware(CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

init_db()

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))

@app.get("/")
def root():
    return {"status": "CrisisIQ online", "version": "1.0"}

@app.get("/api/events")
def get_events(db: Session = Depends(get_db)):
    events = db.query(DisasterEvent).order_by(DisasterEvent.timestamp.desc()).limit(50).all()
    return [{"id": e.id, "title": e.title, "description": e.description,
             "latitude": e.latitude, "longitude": e.longitude,
             "severity": e.severity, "event_type": e.event_type,
             "status": e.status, "ai_assessment": e.ai_assessment,
             "resources_needed": e.resources_needed,
             "predicted_escalation": e.predicted_escalation,
             "alert_message": e.alert_message,
             "confidence": e.confidence,
             "timestamp": e.timestamp.isoformat() if e.timestamp else None,
             "source": e.source} for e in events]

@app.get("/api/resources")
def get_resources(db: Session = Depends(get_db)):
    resources = db.query(Resource).all()
    return [{"id": r.id, "name": r.name, "resource_type": r.resource_type,
             "latitude": r.latitude, "longitude": r.longitude,
             "capacity": r.capacity, "available": r.available,
             "status": r.status} for r in resources]

@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    events = db.query(DisasterEvent).all()
    critical = sum(1 for e in events if e.severity == "critical")
    high = sum(1 for e in events if e.severity == "high")
    return {
        "total_events": len(events),
        "critical": critical,
        "high": high,
        "medium": sum(1 for e in events if e.severity == "medium"),
        "low": sum(1 for e in events if e.severity == "low"),
    }

@app.post("/api/fetch-and-analyze")
def fetch_and_analyze(db: Session = Depends(get_db)):
    all_events = []
    all_events.extend(fetch_earthquakes())
    all_events.extend(fetch_weather_alerts())
    all_events.extend(fetch_news_disasters())

    resources = db.query(Resource).all()
    processed = []

    for raw_event in all_events[:8]:
        try:
            triage_result = triage(raw_event)
            severity = triage_result.get("severity", "medium")

            nearby = []
            for r in resources:
                dist = haversine(raw_event["latitude"], raw_event["longitude"],
                                 r.latitude, r.longitude)
                nearby.append({**{"name": r.name, "resource_type": r.resource_type,
                                  "available": r.available}, "distance_km": dist})
            nearby.sort(key=lambda x: x["distance_km"])

            resource_result = match_resources(raw_event, triage_result, nearby)
            comms_result = draft_alert(raw_event, triage_result, resource_result)
            predict_result = predict_escalation(raw_event, triage_result)

            event = DisasterEvent(
                source=raw_event.get("source", "Unknown"),
                title=raw_event["title"],
                description=raw_event.get("description", ""),
                latitude=raw_event["latitude"],
                longitude=raw_event["longitude"],
                severity=severity,
                event_type=triage_result.get("event_type", "other"),
                ai_assessment=triage_result.get("assessment", ""),
                resources_needed=json.dumps(resource_result),
                predicted_escalation=predict_result.get("escalation_risk", "medium"),
                alert_message=comms_result.get("public_alert", ""),
                confidence=float(predict_result.get("confidence", 85)),
                timestamp=datetime.utcnow(),
                raw_data=json.dumps(raw_event),
            )
            db.add(event)
            processed.append({"title": raw_event["title"], "severity": severity})
        except Exception as e:
            print(f"Error processing event: {e}")
            continue

    db.commit()
    return {"processed": len(processed), "events": processed}
from pydantic import BaseModel

class ChatRequest(BaseModel):
    prompt: str
    system: str = ""

@app.post("/api/ai-chat")
def ai_chat(req: ChatRequest):
    import anthropic
    client = anthropic.Anthropic()
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=600,
        system=req.system or "You are an expert disaster response AI analyst.",
        messages=[{"role": "user", "content": req.prompt}]
    )
    return {"answer": msg.content[0].text}
