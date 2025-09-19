from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, date
import pandas as pd
import numpy as np
from io import StringIO
import requests


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Define Models for Taxi Data
class TaxiTrip(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    pickup_datetime: datetime
    dropoff_datetime: datetime
    pickup_location_id: int
    dropoff_location_id: int
    passenger_count: int
    trip_distance: float
    fare_amount: float
    total_amount: float
    payment_type: int
    trip_duration_minutes: float
    is_delayed: bool  # True if pickup wait time > 10 minutes
    pickup_wait_time_minutes: float

class TripAnalytics(BaseModel):
    total_trips: int
    avg_trip_duration: float
    avg_fare: float
    total_revenue: float
    delayed_trips_count: int
    delay_percentage: float
    avg_wait_time: float

class HourlyAnalytics(BaseModel):
    hour: int
    avg_wait_time: float
    trip_count: int
    delay_percentage: float

class ZoneAnalytics(BaseModel):
    location_id: int
    zone_name: str
    trip_count: int
    avg_wait_time: float
    delay_percentage: float

# Helper functions for data processing
def prepare_for_mongo(data):
    """Convert data types for MongoDB storage"""
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, (datetime, date)):
                data[key] = value.isoformat()
            elif pd.isna(value):
                data[key] = None
    return data

def parse_from_mongo(item):
    """Parse data from MongoDB"""
    if isinstance(item, dict):
        for key, value in item.items():
            if key in ['pickup_datetime', 'dropoff_datetime'] and isinstance(value, str):
                try:
                    item[key] = datetime.fromisoformat(value.replace('Z', '+00:00'))
                except:
                    item[key] = datetime.now(timezone.utc)
    return item

# Data ingestion endpoint
@api_router.post("/ingest-taxi-data")
async def ingest_taxi_data():
    """Ingest NYC TLC taxi data"""
    try:
        # For MVP, we'll create realistic sample data
        # In production, this would fetch from NYC TLC API
        sample_data = generate_sample_taxi_data()
        
        # Clear existing data
        await db.taxi_trips.delete_many({})
        
        # Insert new data
        processed_data = []
        for trip in sample_data:
            trip_dict = prepare_for_mongo(trip.dict())
            processed_data.append(trip_dict)
        
        await db.taxi_trips.insert_many(processed_data)
        
        return {
            "message": "Data ingestion completed",
            "trips_loaded": len(processed_data)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Data ingestion failed: {str(e)}")

def generate_sample_taxi_data(num_trips: int = 1000):
    """Generate realistic sample taxi trip data"""
    np.random.seed(42)  # For reproducible results
    
    trips = []
    base_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
    
    for i in range(num_trips):
        # Random date/time in January 2024
        days_offset = np.random.randint(0, 31)
        hour = np.random.randint(0, 24)
        minute = np.random.randint(0, 60)
        
        pickup_time = base_date.replace(
            day=days_offset + 1,
            hour=hour,
            minute=minute,
            second=np.random.randint(0, 60)
        )
        
        # Trip duration (5-120 minutes)
        trip_duration = max(5, np.random.normal(25, 15))
        
        # Calculate dropoff time properly
        from datetime import timedelta
        dropoff_time = pickup_time + timedelta(minutes=trip_duration)
        
        # Pickup wait time (0-30 minutes, most under 10)
        wait_time = max(0, np.random.exponential(5))
        is_delayed = wait_time > 10
        
        # Location IDs (NYC has ~265 taxi zones)
        pickup_location = np.random.randint(1, 266)
        dropoff_location = np.random.randint(1, 266)
        
        # Trip distance (0.1 - 20 miles)
        distance = max(0.1, np.random.exponential(3))
        
        # Fare calculation (rough NYC taxi rates)
        base_fare = 3.00
        distance_fare = distance * 2.50
        time_fare = trip_duration * 0.50
        fare = base_fare + distance_fare + time_fare
        
        # Total with tips and taxes
        total = fare * np.random.uniform(1.1, 1.3)
        
        trip = TaxiTrip(
            pickup_datetime=pickup_time,
            dropoff_datetime=dropoff_time,
            pickup_location_id=pickup_location,
            dropoff_location_id=dropoff_location,
            passenger_count=np.random.choice([1, 2, 3, 4, 5], p=[0.5, 0.25, 0.15, 0.08, 0.02]),
            trip_distance=round(distance, 2),
            fare_amount=round(fare, 2),
            total_amount=round(total, 2),
            payment_type=np.random.choice([1, 2], p=[0.7, 0.3]),  # 1=credit, 2=cash
            trip_duration_minutes=round(trip_duration, 1),
            is_delayed=is_delayed,
            pickup_wait_time_minutes=round(wait_time, 1)
        )
        trips.append(trip)
    
    return trips

# Analytics endpoints
@api_router.get("/analytics/overview", response_model=TripAnalytics)
async def get_trip_analytics():
    """Get overall trip analytics and KPIs"""
    try:
        trips = await db.taxi_trips.find().to_list(length=None)
        
        if not trips:
            return TripAnalytics(
                total_trips=0, avg_trip_duration=0, avg_fare=0,
                total_revenue=0, delayed_trips_count=0, delay_percentage=0, avg_wait_time=0
            )
        
        total_trips = len(trips)
        avg_duration = sum(trip['trip_duration_minutes'] for trip in trips) / total_trips
        avg_fare = sum(trip['fare_amount'] for trip in trips) / total_trips
        total_revenue = sum(trip['total_amount'] for trip in trips)
        delayed_count = sum(1 for trip in trips if trip['is_delayed'])
        delay_percentage = (delayed_count / total_trips) * 100
        avg_wait_time = sum(trip['pickup_wait_time_minutes'] for trip in trips) / total_trips
        
        return TripAnalytics(
            total_trips=total_trips,
            avg_trip_duration=round(avg_duration, 1),
            avg_fare=round(avg_fare, 2),
            total_revenue=round(total_revenue, 2),
            delayed_trips_count=delayed_count,
            delay_percentage=round(delay_percentage, 1),
            avg_wait_time=round(avg_wait_time, 1)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analytics error: {str(e)}")

@api_router.get("/analytics/hourly", response_model=List[HourlyAnalytics])
async def get_hourly_analytics():
    """Get hourly wait time and delay patterns"""
    try:
        trips = await db.taxi_trips.find().to_list(length=None)
        
        hourly_data = {}
        for trip in trips:
            pickup_dt = datetime.fromisoformat(trip['pickup_datetime'].replace('Z', '+00:00'))
            hour = pickup_dt.hour
            
            if hour not in hourly_data:
                hourly_data[hour] = {
                    'trips': [],
                    'wait_times': [],
                    'delays': []
                }
            
            hourly_data[hour]['trips'].append(trip)
            hourly_data[hour]['wait_times'].append(trip['pickup_wait_time_minutes'])
            hourly_data[hour]['delays'].append(trip['is_delayed'])
        
        result = []
        for hour in range(24):
            if hour in hourly_data:
                data = hourly_data[hour]
                avg_wait = sum(data['wait_times']) / len(data['wait_times'])
                delay_pct = (sum(data['delays']) / len(data['delays'])) * 100
                trip_count = len(data['trips'])
            else:
                avg_wait = 0
                delay_pct = 0
                trip_count = 0
            
            result.append(HourlyAnalytics(
                hour=hour,
                avg_wait_time=round(avg_wait, 1),
                trip_count=trip_count,
                delay_percentage=round(delay_pct, 1)
            ))
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hourly analytics error: {str(e)}")

@api_router.get("/analytics/zones", response_model=List[ZoneAnalytics])
async def get_zone_analytics():
    """Get zone-wise performance analytics"""
    try:
        trips = await db.taxi_trips.find().to_list(length=None)
        
        zone_data = {}
        for trip in trips:
            location_id = trip['pickup_location_id']
            
            if location_id not in zone_data:
                zone_data[location_id] = {
                    'trips': [],
                    'wait_times': [],
                    'delays': []
                }
            
            zone_data[location_id]['trips'].append(trip)
            zone_data[location_id]['wait_times'].append(trip['pickup_wait_time_minutes'])
            zone_data[location_id]['delays'].append(trip['is_delayed'])
        
        result = []
        for location_id, data in zone_data.items():
            avg_wait = sum(data['wait_times']) / len(data['wait_times'])
            delay_pct = (sum(data['delays']) / len(data['delays'])) * 100
            trip_count = len(data['trips'])
            
            # Mock zone names for now
            zone_name = f"Zone {location_id}"
            
            result.append(ZoneAnalytics(
                location_id=location_id,
                zone_name=zone_name,
                trip_count=trip_count,
                avg_wait_time=round(avg_wait, 1),
                delay_percentage=round(delay_pct, 1)
            ))
        
        # Sort by trip count descending and return top 20
        result.sort(key=lambda x: x.trip_count, reverse=True)
        return result[:20]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Zone analytics error: {str(e)}")

# Original test endpoints
@api_router.get("/")
async def root():
    return {"message": "Ride-Hailing Analytics API"}

@api_router.get("/health")
async def health_check():
    try:
        # Test database connection
        await db.taxi_trips.count_documents({})
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()