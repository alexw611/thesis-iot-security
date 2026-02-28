# Brute-Force Angriff Report

## Experiment-Details

| Parameter | Wert |
|-----------|------|
| Datum | 2026-02-04 |
| Uhrzeit | 15:21:22 |
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
| Dauer | 3.41 Sekunden (0.1 Minuten) |
| Versuche durchgeführt | 395 |
| Versuche pro Sekunde | 115.84 |
| Threads | 10 |

### Gefundene Zugangsdaten

| Username | Password |
|----------|----------|
| `admin` | `admin` |


### Sicherheitsmechanismen

| Mechanismus | Implementiert? |
|-------------|----------------|
| Rate-Limiting | ❌ **NEIN** |
| Account-Lockout | ❌ **NEIN** |
| CAPTCHA | ❌ **NEIN** |

## Bewertung

### Schwachstellen

| Schwachstelle | Status |
|---------------|--------|
| Schwache Standard-Credentials | 🔴 **KRITISCH** |
| Fehlendes Rate-Limiting | 🔴 **KRITISCH** - {r.attempts_per_second} Versuche/s möglich |
| Fehlender Account-Lockout | 🔴 **KRITISCH** - Unbegrenzte Versuche |

### CIA-Triade

| Schutzziel | Status | Begründung |
|------------|--------|------------|
| **Confidentiality** | 🔴 KRITISCH | Unbefugter Zugriff mit `admin:admin` möglich |
| **Integrity** | 🔴 GEFÄHRDET | Angreifer kann System manipulieren |
| **Availability** | 🟢 OK | Angriff führte nicht zum Ausfall |

## Fazit

**KRITISCH:** Schwache Standard-Credentials (`admin:admin`) in 395 Versuchen gefunden. Kein Rate-Limiting oder Account-Lockout implementiert.

### Empfehlungen

1. **Starke Passwörter erzwingen** (min. 12 Zeichen, Groß/Klein/Zahlen/Sonderzeichen)
2. **Rate-Limiting** implementieren (max. 5 Versuche pro Minute)
3. **Account-Lockout** nach 10 Fehlversuchen (30 Min Sperre)
4. **Zwei-Faktor-Authentifizierung** (2FA) einführen
5. **Login-Versuche protokollieren** und bei Anomalien alarmieren

---
*Automatisch generiert am 2026-02-04 um 15:21:22*
*Wortlisten: SecLists (https://github.com/danielmiessler/SecLists)*
