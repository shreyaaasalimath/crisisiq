from sqlalchemy import Column, Integer, String, Float, DateTime, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///crisisiq.db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class DisasterEvent(Base):
    __tablename__ = "disaster_events"
    id = Column(Integer, primary_key=True)
    source = Column(String)
    title = Column(String)
    description = Column(Text)
    latitude = Column(Float)
    longitude = Column(Float)
    severity = Column(String)
    event_type = Column(String)
    status = Column(String, default="active")
    ai_assessment = Column(Text)
    resources_needed = Column(Text)
    predicted_escalation = Column(String)
    alert_message = Column(Text)
    confidence = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)
    raw_data = Column(Text)

class Resource(Base):
    __tablename__ = "resources"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    resource_type = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    capacity = Column(Integer)
    available = Column(Integer)
    status = Column(String, default="available")

def init_db():
    Base.metadata.create_all(engine)
    db = SessionLocal()
    if db.query(Resource).count() == 0:
        sample_resources = [
            Resource(name="SF General Hospital", resource_type="hospital", latitude=37.7551, longitude=-122.4057, capacity=500, available=120),
            Resource(name="Red Cross Bay Area", resource_type="shelter", latitude=37.7749, longitude=-122.4194, capacity=800, available=400),
            Resource(name="FEMA Region 9", resource_type="emergency_team", latitude=37.7849, longitude=-122.4094, capacity=50, available=30),
            Resource(name="Oakland Emergency Shelter", resource_type="shelter", latitude=37.8044, longitude=-122.2712, capacity=600, available=300),
            Resource(name="Kaiser Permanente", resource_type="hospital", latitude=37.7833, longitude=-122.4167, capacity=400, available=200),
            Resource(name="National Guard Unit 1", resource_type="rescue_team", latitude=37.3382, longitude=-121.8863, capacity=100, available=80),
        ]
        db.add_all(sample_resources)
        db.commit()
    db.close()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()