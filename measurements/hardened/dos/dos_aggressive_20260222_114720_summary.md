# DoS-Angriff Experiment Report (Aggressive Version - Gehärtetes System)

## Experiment-Details

| Parameter | Wert |
|-----------|------|
| Datum | 2026-02-22 |
| Uhrzeit | 11:47:20 |
| Ziel | http://192.168.0.100:5000 |
| Angriffstyp | HTTP Flood + TCP Flood + Slowloris |
| System | Gehärtet (Login erforderlich) |
| HTTP-Flood Threads | 200 |
| TCP-Flood Threads | 150 |
| Slowloris Threads | 150 |
| **Gesamt Threads** | **500** |
| Dauer | 60 Sekunden |

## Ergebnisse nach Kamera

### Baseline (vor Angriff)

| Kamera | FPS | Latenz (ms) |
|--------|-----|-------------|
| Cam_01 | 21.9 | - |
| Cam_02 | 20.6 | - |
| Cam_03 | 20.5 | - |
| **Durchschnitt** | **21.0** | **5** |

### Während Angriff

| Kamera | FPS | Veränderung |
|--------|-----|-------------|
| Cam_01 | 20.9 | -4.3% |
| Cam_02 | 16.1 | -21.9% |
| Cam_03 | 21.9 | +6.7% |
| **Durchschnitt** | **19.7** | **-6.5%** |

### Angriffs-Statistik

| Metrik | Wert |
|--------|------|
| HTTP Requests gesendet | 9,444 |
| TCP Connections | 17,340 |
| Slowloris Connections | 150 |
| Server-Erfolgsrate | 3.6% |
| Ø Response-Zeit | 175 ms |

### Recovery (nach Angriff)

| Metrik | Wert |
|--------|------|
| Ø Response-Zeit | 36.59 ms |
| Erfolgsrate | 100.0% |
| Zeit bis Recovery | 0.0 Sekunden |

## Bewertung

### Quantitative Auswirkungen

| Metrik | Baseline | Angriff | Veränderung |
|--------|----------|---------|-------------|
| Response-Zeit | 31 ms | 175 ms | +143 ms |
| Erfolgsrate | 100% | 4% | -96% |
| FPS (Durchschnitt) | 21.0 | 19.7 | -6.5% |
| Latenz | 5 ms | 11 ms | +125.4% |

### Gesamtbewertung

**Auswirkung auf Verfügbarkeit:** KRITISCH - Dashboard nicht erreichbar

**Schwachstelle bestätigt:** ✅ Ja

### CIA-Triade Bewertung

| Schutzziel | Status | Begründung |
|------------|--------|------------|
| **Confidentiality** | ⚪ Nicht betroffen | Kein Datenleck durch diesen Angriff |
| **Integrity** | ⚪ Nicht betroffen | Keine Datenmanipulation |
| **Availability** | 🔴 KRITISCH | KRITISCH - Dashboard nicht erreichbar |

## Fazit

Der kombinierte DoS-Angriff war **erfolgreich**. Das Dashboard war während des Angriffs 
weitgehend nicht erreichbar (Erfolgsrate: 3.6%). 

Trotz der Härtung (Login-Schutz) konnte der Angriff die Verfügbarkeit stark 
beeinträchtigen. Die Authentifizierung schützt zwar vor unauthorisiertem Zugriff, 
bietet aber keinen ausreichenden Schutz gegen volumetrische DoS-Angriffe.

**Empfehlung:** Implementierung von Rate-Limiting, Connection-Pooling und 
eventuell einen Reverse-Proxy (nginx) vor dem Flask-Server.

---
*Automatisch generiert am 2026-02-22 um 11:47:20*
*Tool: DoS-Attack-Script für Bachelorarbeit IoT-Sicherheitsanalyse*
*Variante: Gehärtetes System mit Authentifizierung*
