import os
import json
from datetime import datetime

import boto3
import requests
from dotenv import load_dotenv

load_dotenv()

# ---- CONFIGURATION ----
API_KEY = os.getenv("OPENWEATHER_API_KEY")
VILLES = ["Marrakech", "Tanger", "Dakhla", "Essaouira"]

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://127.0.0.1:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")

if not API_KEY:
    raise SystemExit("OPENWEATHER_API_KEY is missing. Copy .env.example to .env and set it.")

# Connexion à MinIO (notre Data Lake local)
s3 = boto3.client(
    "s3",
    endpoint_url=MINIO_ENDPOINT,
    aws_access_key_id=MINIO_ACCESS_KEY,
    aws_secret_access_key=MINIO_SECRET_KEY
)

# ---- INGESTION ----
date_aujourd_hui = datetime.now().strftime("%Y-%m-%d")
heure = datetime.now().strftime("%Hh%M")

for ville in VILLES:
    # 1. Appeler l'API
    url = f"https://api.openweathermap.org/data/2.5/weather?q={ville}&appid={API_KEY}&units=metric"
    reponse = requests.get(url)
    donnees = reponse.json()

    # 2. Préparer le chemin dans MinIO
    chemin = f"weather_raw/city={ville}/date={date_aujourd_hui}/data_{heure}.json"

    # 3. Envoyer dans MinIO
    s3.put_object(
        Bucket="bronze",
        Key=chemin,
        Body=json.dumps(donnees),
        ContentType="application/json"
    )

    print(f"✅ {ville} → stocké dans MinIO : {chemin}")

print("\n🎉 Ingestion terminée !")