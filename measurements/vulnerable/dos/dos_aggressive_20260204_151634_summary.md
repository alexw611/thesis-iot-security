# DoS-Angriff Experiment Report (Aggressive Version)

## Experiment-Details

| Parameter | Wert |
|-----------|------|
| Datum | 2026-02-04 |
| Uhrzeit | 15:16:34 |
| Ziel | http://192.168.0.100:5000 |
| Angriffstyp | HTTP Flood + TCP Flood + Slowloris |
| HTTP-Flood Threads | 200 |
| TCP-Flood Threads | 150 |
| Slowloris Threads | 150 |
| **Gesamt Threads** | **500** |
| Dauer | 60 Sekunden |

## Ergebnisse nach Kamera

### Baseline (vor Angriff)

| Kamera | FPS | Latenz (ms) |
|--------|-----|-------------|
| Cam_01 | 20.9 | - |
| Cam_02 | 13.9 | - |
| Cam_03 | 24.0 | - |
| **Durchschnitt** | **19.6** | **19** |

### Während Angriff

| Kamera | FPS | Veränderung |
|--------|-----|-------------|
| Cam_01 | 12.6 | -39.6% |
| Cam_02 | 7.0 | -49.7% |
| Cam_03 | 18.7 | -22.3% |
| **Durchschnitt** | **0.2** | **-98.8%** |

### Angriffs-Statistik

| Metrik | Wert |
|--------|------|
| HTTP Requests gesendet | 5,432 |
| TCP Connections | 11,484 |
| Slowloris Connections | 150 |
| Server-Erfolgsrate | 1.8% |
| Ø Response-Zeit | 669 ms |

### Recovery (nach Angriff)

| Metrik | Wert |
|--------|------|
| Ø Response-Zeit | 90.76 ms |
| Erfolgsrate | 100.0% |
| Zeit bis Recovery | 0.0 Sekunden |

## Bewertung

### Quantitative Auswirkungen

| Metrik | Baseline | Angriff | Veränderung |
|--------|----------|---------|-------------|
| Response-Zeit | 156 ms | 669 ms | +513 ms |
| Erfolgsrate | 100% | 2% | -98% |
| FPS (Durchschnitt) | 19.6 | 0.2 | -98.8% |
| Latenz | 19 ms | 0 ms | -99.8% |

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
weitgehend nicht erreichbar (Erfolgsrate: 1.8%). 

Dies bestätigt die Hypothese, dass der Flask-Server auf dem Raspberry Pi anfällig für 
Denial-of-Service-Angriffe ist, wenn mehrere Angriffsvektoren (HTTP Flood, TCP Flood, 
Slowloris) kombiniert werden.

**Empfehlung:** Implementierung von Rate-Limiting, Connection-Pooling und 
eventuell einen Reverse-Proxy (nginx) vor dem Flask-Server.

---
*Automatisch generiert am 2026-02-04 um 15:16:34*
*Tool: DoS-Attack-Script für Bachelorarbeit IoT-Sicherheitsanalyse*
