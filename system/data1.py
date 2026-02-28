# Erstellt mit Claude Opus 4.5 am 04.02.2026

import requests
import time
import csv
import os
from datetime import datetime
from collections import defaultdict

SERVER_URL = "http://192.168.0.100:5000"
MEASUREMENT_INTERVAL = 5  
TOTAL_DURATION = 45       
OUTPUT_DIR = "messdaten_insecure"

USERNAME = "admin"
PASSWORD = "admin"

def create_session():
    session = requests.Session()
    
    login_data = {
        "username": USERNAME,
        "password": PASSWORD
    }
    
    try:
        response = session.post(f"{SERVER_URL}/", data=login_data, allow_redirects=True)
        if "Dashboard" in response.text or response.url.endswith("/dashboard"):
            print("✅ Login erfolgreich")
            return session
        else:
            print("❌ Login fehlgeschlagen")
            return None
    except Exception as e:
        print(f"❌ Verbindungsfehler: {e}")
        return None

def get_measurements(session):
    try:
        response = session.get(f"{SERVER_URL}/status", timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"⚠️ Status-Fehler: {response.status_code}")
            return None
    except Exception as e:
        print(f"⚠️ Messfehler: {e}")
        return None

def run_measurement():
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_filename = f"{OUTPUT_DIR}/messdaten_insecure_{timestamp}.csv"
    
    print("=" * 70)
    print("  MESSDATEN-ERFASSUNG - UNSICHERES SYSTEM")
    print("  TCP Klartext - Keine Verschlüsselung")
    print("=" * 70)
    print(f"  Intervall:     {MEASUREMENT_INTERVAL} Sekunden")
    print(f"  Gesamtdauer:   {TOTAL_DURATION} Sekunden")
    print(f"  Ausgabedatei:  {csv_filename}")
    print("=" * 70)
    print()
    
    session = create_session()
    if not session:
        print("❌ Abbruch: Login nicht möglich")
        return
    
    all_measurements = defaultdict(list)
    time_points = []
    
    initial_data = get_measurements(session)
    if not initial_data or not initial_data.get("cameras"):
        print("❌ Keine Kameras gefunden")
        return
    
    camera_names = sorted([cam["name"] for cam in initial_data["cameras"]])
    print(f"📷 Gefundene Kameras: {', '.join(camera_names)}")
    print()
    
    csv_header = ["Zeitpunkt (t)"]
    for cam in camera_names:
        csv_header.extend([
            f"{cam}_FPS_geglaettet",
            f"{cam}_FPS_Min",
            f"{cam}_FPS_Max",
            f"{cam}_Standardabweichung",
            f"{cam}_Latenz"
        ])
    
    with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile, delimiter=';')
        writer.writerow(csv_header)
        
        start_time = time.time()
        measurement_count = 0
        
        while True:
            current_t = measurement_count * MEASUREMENT_INTERVAL
            
            if current_t > TOTAL_DURATION:
                break
            
            data = get_measurements(session)
            
            if data and data.get("cameras"):
                csv_row = [f"t = {current_t}"]
                
                print(f"[t = {current_t:2d}s] ", end="")
                
                for cam in camera_names:
                    cam_data = next((c for c in data["cameras"] if c["name"] == cam), None)
                    
                    if cam_data:
                        fps = cam_data.get("fps", 0)
                        fps_min = cam_data.get("fps_min", 0)
                        fps_max = cam_data.get("fps_max", 0)
                        fps_std = cam_data.get("fps_std", 0)
                        latency = cam_data.get("latency", 0)
                        
                        all_measurements[cam].append({
                            "t": current_t,
                            "fps": fps,
                            "fps_min": fps_min,
                            "fps_max": fps_max,
                            "fps_std": fps_std,
                            "latency": latency
                        })
                        
                        csv_row.extend([
                            f"{fps:.1f}".replace(".", ","),
                            f"{fps_min:.1f}".replace(".", ","),
                            f"{fps_max:.1f}".replace(".", ","),
                            f"{fps_std:.2f}".replace(".", ","),
                            f"{int(latency)}ms"
                        ])
                        
                        print(f"{cam}: {fps:.1f} FPS, {int(latency)}ms | ", end="")
                    else:
                        csv_row.extend(["", "", "", "", ""])
                        print(f"{cam}: OFFLINE | ", end="")
                
                print()
                writer.writerow(csv_row)
                csvfile.flush()
                
            else:
                print(f"[t = {current_t:2d}s] ⚠️ Keine Daten")
            
            measurement_count += 1
            time_points.append(current_t)
            
            if current_t < TOTAL_DURATION:
                next_measurement = start_time + (measurement_count * MEASUREMENT_INTERVAL)
                sleep_time = next_measurement - time.time()
                if sleep_time > 0:
                    time.sleep(sleep_time)
    
    print()
    print("=" * 70)
    print("  MESSUNG ABGESCHLOSSEN")
    print("=" * 70)
    print(f"  📁 CSV gespeichert: {csv_filename}")
    print()
    print("  ZUSAMMENFASSUNG:")
    print("-" * 70)
    for cam in camera_names:
        if all_measurements[cam]:
            measurements = all_measurements[cam]
            avg_fps = sum(m["fps"] for m in measurements) / len(measurements)
            avg_latency = sum(m["latency"] for m in measurements) / len(measurements)
            min_latency = min(m["latency"] for m in measurements)
            max_latency = max(m["latency"] for m in measurements)
            
            print(f"  {cam}:")
            print(f"    Ø FPS:           {avg_fps:.1f}")
            print(f"    Ø Latenz:        {avg_latency:.0f}ms")
            print(f"    Latenz-Bereich:  {min_latency:.0f}ms - {max_latency:.0f}ms")
            print()
    
    create_excel_format(csv_filename, camera_names, all_measurements, time_points)
    
    print("=" * 70)
    print("✅ Fertig!")
    print("=" * 70)

def create_excel_format(base_filename, camera_names, all_measurements, time_points):
    
    excel_filename = base_filename.replace(".csv", "_excel_format.csv")
    
    with open(excel_filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, delimiter=';')
        
        header = [""] + [f"t = {t}" for t in time_points]
        writer.writerow(header)
        
        for cam in camera_names:
            writer.writerow([])
            writer.writerow([cam])
            
            measurements = all_measurements[cam]
            
            if measurements:
                row = ["FPS (geglättet)"]
                row.extend([f"{m['fps']:.1f}".replace(".", ",") for m in measurements])
                writer.writerow(row)
                
                row = ["FPS Min"]
                row.extend([f"{m['fps_min']:.1f}".replace(".", ",") for m in measurements])
                writer.writerow(row)
                
                row = ["FPS Max"]
                row.extend([f"{m['fps_max']:.1f}".replace(".", ",") for m in measurements])
                writer.writerow(row)
                
                row = ["Standardabweichung"]
                row.extend([f"{m['fps_std']:.2f}".replace(".", ",") for m in measurements])
                writer.writerow(row)
                
                row = ["Latenz"]
                row.extend([f"{int(m['latency'])}ms" for m in measurements])
                writer.writerow(row)
    
    print(f"  📊 Excel-Format: {excel_filename}")

if __name__ == "__main__":
    try:
        run_measurement()
    except KeyboardInterrupt:
        print("\n\n⚠️ Messung abgebrochen (Ctrl+C)")
    except Exception as e:
        print(f"\n❌ Fehler: {e}")
