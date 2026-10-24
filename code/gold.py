import boto3
import json
from datetime import datetime, timezone

import os
from dotenv import load_dotenv

load_dotenv()

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
SILVER_BUCKET = "silver"
GOLD_BUCKET = "gold"

# Les 4 fichiers Silver
SILVER_FILES = [
    "weather_clean/city=Dakhla/date=2026-04-12/data_clean.json",
    "weather_clean/city=Mogador/date=2026-04-12/data_clean.json",
    "weather_clean/city=Marrakesh/date=2026-04-12/data_clean.json",
    "weather_clean/city=Tangier/date=2026-04-12/data_clean.json",
]

# ---- CONNEXION MINIO ----
s3 = boto3.client(
    "s3",
    endpoint_url=MINIO_ENDPOINT,
    aws_access_key_id=MINIO_ACCESS_KEY,
    aws_secret_access_key=MINIO_SECRET_KEY,
)

# Créer bucket gold si nécessaire
existing_buckets = [b["Name"] for b in s3.list_buckets()["Buckets"]]
if GOLD_BUCKET not in existing_buckets:
    s3.create_bucket(Bucket=GOLD_BUCKET)
    print("✅ Bucket 'gold' créé.")
else:
    print("✅ Bucket 'gold' existe déjà.")


# ---- FONCTION CALCUL SCORE MÉTÉO ----
def calculer_score(data):
    """
    Score météo sur 100 basé sur 3 critères :
    - Température idéale entre 18°C et 28°C → max 40 points
    - Humidité agréable entre 40% et 60%    → max 30 points
    - Vent faible < 5 m/s                   → max 30 points
    """
    score = 0

    # 1. Score température (idéale entre 18 et 28°C)
    temp = data.get("temperature_c", None)
    if temp is not None:
        if 18 <= temp <= 28:
            score_temp = 40
        elif 15 <= temp < 18 or 28 < temp <= 32:
            score_temp = 25
        elif 10 <= temp < 15 or 32 < temp <= 38:
            score_temp = 10
        else:
            score_temp = 0
        score += score_temp

    # 2. Score humidité (idéale entre 40% et 60%)
    humidity = data.get("humidite_pct", None)
    if humidity is not None:
        if 40 <= humidity <= 60:
            score_humidity = 30
        elif 30 <= humidity < 40 or 60 < humidity <= 70:
            score_humidity = 20
        elif 20 <= humidity < 30 or 70 < humidity <= 80:
            score_humidity = 10
        else:
            score_humidity = 0
        score += score_humidity

    # 3. Score vent (idéal < 5 m/s)
    wind = data.get("vent_vitesse_ms", None)
    if wind is not None:
        if wind < 5:
            score_wind = 30
        elif 5 <= wind < 10:
            score_wind = 20
        elif 10 <= wind < 15:
            score_wind = 10
        else:
            score_wind = 0
        score += score_wind

    return score


# ---- TRAITEMENT ----
print("\n🚀 Démarrage transformation Gold...\n")

villes_data = []

for silver_key in SILVER_FILES:
    try:
        obj = s3.get_object(Bucket=SILVER_BUCKET, Key=silver_key)
        data = json.loads(obj["Body"].read().decode("utf-8"))
        print(f"📥 Lu : {silver_key}")

        score = calculer_score(data)
        data["score_meteo"] = score
        villes_data.append(data)

    except Exception as e:
        print(f"❌ Erreur pour {silver_key} : {e}\n")

# ---- CLASSEMENT ----
villes_data.sort(key=lambda x: x["score_meteo"], reverse=True)

print("\n📊 Classement des villes :\n")
for i, ville in enumerate(villes_data):
    meilleure = "🏆 MEILLEURE VILLE" if i == 0 else ""
    ville["classement"] = i + 1
    ville["meilleure_ville"] = True if i == 0 else False
    ville["date"] = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    print(f"  {i+1}. {ville['ville']} → Score: {ville['score_meteo']}/100 {meilleure}")

# ---- SAUVEGARDE DANS GOLD ----
print("\n💾 Sauvegarde dans Gold...\n")

date_today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")

for ville in villes_data:
    gold_key = f"weather_analytics/date={date_today}/city={ville['ville']}/data_gold.json"
    s3.put_object(
        Bucket=GOLD_BUCKET,
        Key=gold_key,
        Body=json.dumps(ville, ensure_ascii=False, indent=2).encode("utf-8"),
        ContentType="application/json",
    )
    print(f"✅ Sauvegardé : gold/{gold_key}")

print("\n🎉 Gold Layer terminé !")
print(f"🏆 Meilleure ville pour le weekend : {villes_data[0]['ville']} ({villes_data[0]['score_meteo']}/100)")