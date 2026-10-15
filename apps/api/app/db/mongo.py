from functools import lru_cache

from pymongo import MongoClient

from app.core.config import get_settings


@lru_cache
def mongo_database():
    settings = get_settings()
    client = MongoClient(settings.mongodb_url, serverSelectionTimeoutMS=2000, connectTimeoutMS=2000)
    return client[settings.mongodb_database]


def ensure_indexes(database):
    database.civic_events.create_index([("aggregate_id", 1), ("created_at", -1)])
    database.civic_events.create_index([("event_type", 1), ("created_at", -1)])
    database.road_observations.create_index([("location", "2dsphere")])
    database.road_observations.create_index([("road_id", 1), ("observed_at", -1)])
    # Reserved for future IoT; UTC BSON datetimes expire after 90 days.
    database.iot_readings.create_index("observed_at", expireAfterSeconds=90 * 86400)
    database.iot_readings.create_index([("device_id", 1), ("observed_at", -1)])
