# Brute-Force Angriff Report

## Experiment-Details

| Parameter | Wert |
|-----------|------|
| Datum | 2026-02-22 |
| Uhrzeit | 11:09:03 |
| Ziel | http://192.168.0.100:5000/ |

### Wortlisten

| Typ | Quelle | Anzahl |
|-----|--------|--------|
| Benutzernamen | SecLists (GitHub) | 17 |
| Passwörter | SecLists - 10k Most Common | 1000 |
| **Kombinationen** | - | **17,000** |

## Ergebnisse

### Timing

| Metrik | Wert |
|--------|------|
| Dauer | 356.65 Sekunden (5.9 Minuten) |
| Versuche durchgeführt | 17,000 |
| Versuche pro Sekunde | 47.67 |
| Threads | 10 |

### Gefundene Zugangsdaten

*Keine Zugangsdaten gefunden*

### Sicherheitsmechanismen

| Mechanismus | Implementiert? |
|-------------|----------------|
| Rate-Limiting | ❌ **NEIN** |
| Account-Lockout | ✅ Ja |
| CAPTCHA | ❌ **NEIN** |

## Bewertung

### Schwachstellen

| Schwachstelle | Status |
|---------------|--------|
| Schwache Standard-Credentials | 🟢 Nicht gefunden |
| Fehlendes Rate-Limiting | 🔴 **KRITISCH** - {r.attempts_per_second} Versuche/s möglich |
| Fehlender Account-Lockout | 🟢 Vorhanden |

### CIA-Triade

| Schutzziel | Status | Begründung |
|------------|--------|------------|
| **Confidentiality** | 🟢 OK | Keine schwachen Credentials |
| **Integrity** | 🟢 OK | - |
| **Availability** | 🟢 OK | Angriff führte nicht zum Ausfall |

## Fazit

Keine schwachen Credentials gefunden.

### Empfehlungen

1. **Starke Passwörter erzwingen** (min. 12 Zeichen, Groß/Klein/Zahlen/Sonderzeichen)
2. **Rate-Limiting** implementieren (max. 5 Versuche pro Minute)
3. **Account-Lockout** nach 10 Fehlversuchen (30 Min Sperre)
4. **Zwei-Faktor-Authentifizierung** (2FA) einführen
5. **Login-Versuche protokollieren** und bei Anomalien alarmieren

---
*Automatisch generiert am 2026-02-22 um 11:09:03*
*Wortlisten: SecLists (https://github.com/danielmiessler/SecLists)*
