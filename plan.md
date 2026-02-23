Ziel
Eine REST-API in Python mit FastAPI, die den Hintergrund von gelieferten Bildern entfernt. Betrieb im Docker-Container per Docker Compose. Bildverarbeitung mit OpenCV.

Meilensteine und Aufgaben

M1 - Projektgrundlage
- Repository-Struktur anlegen (src/, tests/, Dockerfile, docker-compose.yml, requirements.txt, .env.example, .gitignore)
- Basis-Konfiguration fuer FastAPI und Uvicorn
- Lokale Start- und Docker-Startanleitung dokumentieren

M2 - API Grundfunktion
- FastAPI-App mit Health-Check und Version-Endpoint
- Datei-Upload-Endpoint fuer Bilder
- Validierung (Dateityp, maximale Groesse, Fehlerbehandlung)

M3 - Hintergrund-Entfernung
- OpenCV-Pipeline fuer Background-Removal (GrabCut als Startpunkt)
- PNG-Output mit Alpha-Kanal
- Rueckgabe als StreamingResponse

M4 - Containerisierung
- Dockerfile fuer schlanken Runtime-Container
- docker-compose.yml mit Port-Mapping und Volume-Option
- Environment-Konfiguration (.env)

M5 - Tests und Qualitaet
- Basis-Tests fuer Health-Check und Upload-Flow
- Beispielbild und Dokumentation zur Nutzung

Umsetzungshinweise
- Alle Endpunkte liefern JSON-Fehler mit klaren Messages
- Bildverarbeitung erfolgt im Speicher (keine Dateischreibungen)
- API-Timeouts und Bildgroessen-Grenzen konfigurieren