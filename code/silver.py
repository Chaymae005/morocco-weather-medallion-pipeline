import boto3
import json
from datetime import datetime, timezone

import os
from dotenv import load_dotenv

load_dotenv()

# ---- CONFIGURATION ----
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
BRONZE_BUCKET = "bronze"
SILVER_BUCKET = "silver"

BRONZE_FILES = [
    "weather_raw/city=Dakhla/date=2026-04-12/data_23h40.json",
    "weather_raw/city=Essaouira/date=2026-04-12/data_23h40.json",
    "weather_raw/city=Marrakech/date=2026-04-12/data_23h40.json",
    "weather_raw/city=Tanger/date=2026-04-12/data_23h40.json",
]

s3 = boto3.client(
    "s3",
    endpoint_url=MINIO_ENDPOINT,
    aws_access_key_id=MINIO_ACCESS_KEY,
    aws_secret_access_key=MINIO_SECRET_KEY,
)

# Créer bucket silver si nécessaire
existing_buckets = [b["Name"] for b in s3.list_buckets()["Buckets"]]
if SILVER_BUCKET not in existing_buckets:
    s3.create_bucket(Bucket=SILVER_BUCKET)
    print("✅ Bucket 'silver' créé.")
else:
    print("✅ Bucket 'silver' existe déjà.")

def transformer_donnees(raw):
    dt_unix = raw.get("dt", None)
    if dt_unix:
        event_timestamp = datetime.fromtimestamp(dt_unix, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    else:
        event_timestamp = None

    ingestion_timestamp = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    temperature = raw.get("main", {}).get("temp", None)
    humidity = raw.get("main", {}).get("humidity", None)
    wind_speed = raw.get("wind", {}).get("speed", None)

    # Nettoyage valeurs aberrantes
    if temperature is not None and (temperature < -50 or temperature > 60):
        temperature = None
    if humidity is not None and (humidity < 0 or humidity > 100):
        humidity = None
    if wind_speed is not None and wind_speed < 0:
        wind_speed = None

    return {
        "ville": raw.get("name", None),
        "longitude": raw.get("coord", {}).get("lon", None),
        "latitude": raw.get("coord", {}).get("lat", None),
        "temperature_c": round(temperature, 2) if temperature is not None else None,
        "feels_like_c": round(raw.get("main", {}).get("feels_like", 0), 2),
        "temp_min_c": round(raw.get("main", {}).get("temp_min", 0), 2),
        "temp_max_c": round(raw.get("main", {}).get("temp_max", 0), 2),
        "pression_hpa": raw.get("main", {}).get("pressure", None),
        "humidite_pct": humidity,
        "meteo": raw.get("weather", [{}])[0].get("main", None),
        "description_meteo": raw.get("weather", [{}])[0].get("description", None),
        "vent_vitesse_ms": round(wind_speed, 2) if wind_speed is not None else None,
        "vent_direction_deg": raw.get("wind", {}).get("deg", None),
        "nuages_pct": raw.get("clouds", {}).get("all", None),
        "visibilite_m": raw.get("visibility", None),
        "event_timestamp": event_timestamp,
        "ingestion_timestamp": ingestion_timestamp,
    }

print("\n🚀 Démarrage transformation Silver...\n")

for bronze_key in BRONZE_FILES:
    try:
        obj = s3.get_object(Bucket=BRONZE_BUCKET, Key=bronze_key)
        raw_data = json.loads(obj["Body"].read().decode("utf-8"))
        print(f"📥 Lu : {bronze_key}")

        silver_data = transformer_donnees(raw_data)
        ville = silver_data["ville"]
        date = silver_data["event_timestamp"][:10] if silver_data["event_timestamp"] else "unknown"

        silver_key = f"weather_clean/city={ville}/date={date}/data_clean.json"
        s3.put_object(
            Bucket=SILVER_BUCKET,
            Key=silver_key,
            Body=json.dumps(silver_data, ensure_ascii=False, indent=2).encode("utf-8"),
            ContentType="application/json",
        )
        print(f"✅ Sauvegardé : silver/{silver_key}")
        print(f"   → Ville: {ville} | Temp: {silver_data['temperature_c']}°C | Humidité: {silver_data['humidite_pct']}% | Vent: {silver_data['vent_vitesse_ms']} m/s\n")

    except Exception as e:
        print(f"❌ Erreur pour {bronze_key} : {e}\n")

print("🎉 Silver Layer terminé !")