import boto3
import json

import os
from dotenv import load_dotenv

load_dotenv()

# ---- CONFIGURATION ----
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")

s3 = boto3.client(
    "s3",
    endpoint_url=MINIO_ENDPOINT,
    aws_access_key_id=MINIO_ACCESS_KEY,
    aws_secret_access_key=MINIO_SECRET_KEY,
)

print("🧪 Démarrage des tests qualité...\n")
erreurs = 0

# =============================
# TEST 1 — Bronze : fichiers existent
# =============================
print("📦 TEST 1 : Vérification Bronze...")
BRONZE_FILES = [
    "weather_raw/city=Dakhla/date=2026-04-12/data_23h40.json",
    "weather_raw/city=Essaouira/date=2026-04-12/data_23h40.json",
    "weather_raw/city=Marrakech/date=2026-04-12/data_23h40.json",
    "weather_raw/city=Tanger/date=2026-04-12/data_23h40.json",
]
for f in BRONZE_FILES:
    try:
        s3.head_object(Bucket="bronze", Key=f)
        print(f"  ✅ Existe : {f}")
    except:
        print(f"  ❌ MANQUANT : {f}")
        erreurs += 1

# =============================
# TEST 2 — Silver : types et valeurs
# =============================
print("\n🥈 TEST 2 : Vérification Silver...")
SILVER_FILES = [
    "weather_clean/city=Dakhla/date=2026-04-12/data_clean.json",
    "weather_clean/city=Mogador/date=2026-04-12/data_clean.json",
    "weather_clean/city=Marrakesh/date=2026-04-12/data_clean.json",
    "weather_clean/city=Tangier/date=2026-04-12/data_clean.json",
]
for f in SILVER_FILES:
    try:
        obj = s3.get_object(Bucket="silver", Key=f)
        data = json.loads(obj["Body"].read().decode("utf-8"))

        ville = data.get("ville", "?")

        # Vérif température
        temp = data.get("temperature_c")
        if temp is None:
            print(f"  ❌ {ville} : température manquante")
            erreurs += 1
        elif not (-50 <= temp <= 60):
            print(f"  ❌ {ville} : température aberrante ({temp}°C)")
            erreurs += 1
        else:
            print(f"  ✅ {ville} : température OK ({temp}°C)")

        # Vérif humidité
        hum = data.get("humidite_pct")
        if hum is None:
            print(f"  ❌ {ville} : humidité manquante")
            erreurs += 1
        elif not (0 <= hum <= 100):
            print(f"  ❌ {ville} : humidité aberrante ({hum}%)")
            erreurs += 1
        else:
            print(f"  ✅ {ville} : humidité OK ({hum}%)")

        # Vérif vent
        vent = data.get("vent_vitesse_ms")
        if vent is None:
            print(f"  ❌ {ville} : vent manquant")
            erreurs += 1
        elif vent < 0:
            print(f"  ❌ {ville} : vent négatif ({vent})")
            erreurs += 1
        else:
            print(f"  ✅ {ville} : vent OK ({vent} m/s)")

        # Vérif timestamps
        if not data.get("event_timestamp"):
            print(f"  ❌ {ville} : event_timestamp manquant")
            erreurs += 1
        else:
            print(f"  ✅ {ville} : timestamps OK")

    except Exception as e:
        print(f"  ❌ Erreur lecture {f} : {e}")
        erreurs += 1

# =============================
# TEST 3 — Gold : scores valides
# =============================
print("\n🥇 TEST 3 : Vérification Gold...")
GOLD_FILES = [
    "weather_analytics/date=2026-05-09/city=Tangier/data_gold.json",
    "weather_analytics/date=2026-05-09/city=Marrakesh/data_gold.json",
    "weather_analytics/date=2026-05-09/city=Mogador/data_gold.json",
    "weather_analytics/date=2026-05-09/city=Dakhla/data_gold.json",
]
for f in GOLD_FILES:
    try:
        obj = s3.get_object(Bucket="gold", Key=f)
        data = json.loads(obj["Body"].read().decode("utf-8"))

        ville = data.get("ville", "?")
        score = data.get("score_meteo")
        classement = data.get("classement")

        if score is None:
            print(f"  ❌ {ville} : score manquant")
            erreurs += 1
        elif not (0 <= score <= 100):
            print(f"  ❌ {ville} : score invalide ({score})")
            erreurs += 1
        else:
            print(f"  ✅ {ville} : score OK ({score}/100)")

        if classement is None:
            print(f"  ❌ {ville} : classement manquant")
            erreurs += 1
        else:
            print(f"  ✅ {ville} : classement OK (#{classement})")

    except Exception as e:
        print(f"  ❌ Erreur lecture {f} : {e}")
        erreurs += 1

# =============================
# RÉSULTAT FINAL
# =============================
print("\n" + "="*40)
if erreurs == 0:
    print("🎉 TOUS LES TESTS SONT PASSÉS !")
else:
    print(f"⚠️ {erreurs} ERREUR(S) DÉTECTÉE(S) !")
print("="*40)