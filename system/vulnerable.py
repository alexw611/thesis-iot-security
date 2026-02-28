# Claude Opus 4.5 am 17.01.2026

import socket
import threading
import time
import math
from collections import defaultdict
from flask import Flask, Response, redirect, url_for, session, request

TCP_PORT = 9000
HTTP_PORT = 5000
CAMERA_TIMEOUT = 15.0

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin"

frames = {}
fps = defaultdict(float)
last_ts = {}
frame_id = defaultdict(int)
lock = threading.Lock()

frame_times = defaultdict(list)
latency_samples = defaultdict(list)
esp_offset = {}

def tcp_server():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
    s.bind(("0.0.0.0", TCP_PORT))
    s.listen(10)
    print(f"[TCP-INSECURE] Port {TCP_PORT} - Klartext")
    while True:
        conn, addr = s.accept()
        conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        print(f"[TCP] {addr} connected")
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

def handle_client(conn, addr):
    buf = b""
    count = 0
    
    while True:
        try:
            data = conn.recv(16384)
            if not data:
                break
            buf += data
            
            while True:
                newline_pos = buf.find(b"\n")
                if newline_pos == -1:
                    break 
                
                header_bytes = buf[:newline_pos]
                rest = buf[newline_pos + 1:]
                
                try:
                    header = header_bytes.decode('ascii')
                except:
                    cam_pos = buf.find(b"CAM:")
                    if cam_pos > 0:
                        buf = buf[cam_pos:]
                    else:
                        buf = rest
                    continue
                
                parts = header.split(":")
                
                # Protokoll: CAM:<name>:<size>:<timestamp>
                if len(parts) < 4 or parts[0] != "CAM":
                    buf = rest
                    continue
                
                cam = parts[1]
                try:
                    length = int(parts[2])
                    esp_epoch_ms = int(parts[3])
                except ValueError:
                    buf = rest
                    continue
                
                if len(rest) < length:
                    break  
                
                jpeg = rest[:length]
                buf = rest[length:]
                
                now = time.time()
                with lock:
                    if cam in last_ts:
                        dt = now - last_ts[cam]
                        if dt > 0:
                            fps[cam] = fps.get(cam, 0) * 0.95 + (1.0/dt) * 0.05
                    last_ts[cam] = now
                    frames[cam] = jpeg
                    frame_id[cam] += 1
                    
                    frame_times[cam].append(now)
                    if len(frame_times[cam]) > 200:
                        frame_times[cam] = frame_times[cam][-100:]
                    
                    if esp_epoch_ms > 1000000000000:
                        server_ms = now * 1000
                        latency = server_ms - esp_epoch_ms
                        if 0 < latency < 5000:
                            latency_samples[cam].append(latency)
                            if len(latency_samples[cam]) > 100:
                                latency_samples[cam] = latency_samples[cam][-50:]
                
                count += 1
                if count % 50 == 0:
                    print(f"[INSECURE] {cam}: {count} Frames empfangen")
                
        except Exception as e:
            print(f"[TCP] Error: {e}")
            break
    
    print(f"[TCP] {addr} disconnected - Frames: {count}")
    conn.close()

app = Flask(__name__)
app.secret_key = "unsicher"  

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("dashboard"))
        return "Falsch"
    
    return """
    <style>
        body{background:#0a0a0a;color:#fff;font-family:system-ui;display:flex;
             justify-content:center;align-items:center;height:100vh;margin:0}
        .box{background:#1a1a2e;padding:40px;border-radius:16px}
        h2{margin:0 0 20px 0;text-align:center}
        input{display:block;margin:12px 0;padding:12px;width:220px;
              background:#16213e;border:1px solid #334155;color:#fff;border-radius:8px}
        button{padding:12px;background:#ef4444;border:none;color:#fff;
               cursor:pointer;border-radius:8px;width:100%;font-weight:bold}
        button:hover{background:#dc2626}
    </style>
    <div class="box">
        <h2>⚠️ INSECURE Admin Login</h2>
        <form method="post">
            <input name="username" placeholder="Username">
            <input type="password" name="password" placeholder="Password">
            <button>Login</button>
        </form>
    </div>
    """

@app.route("/dashboard")
def dashboard():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    
    return """
    <style>
        body{background:#0a0a0a;color:#fff;font-family:system-ui;padding:20px;margin:0}
        .header{display:flex;justify-content:space-between;align-items:center;margin-bottom:20px}
        .logout-btn{background:#ef4444;color:#fff;padding:10px 20px;border-radius:8px;
                    text-decoration:none;font-weight:bold}
        .grid{display:flex;flex-wrap:wrap;gap:20px}
        .cam{background:#1a1a2e;padding:20px;border-radius:16px;width:500px}
        .cam h3{margin:0 0 10px 0}
        .cam img{width:100%;border:2px solid #ef4444;border-radius:8px;background:#000}
        .metrics{background:#16213e;padding:10px;border-radius:8px;margin-bottom:10px;
                 font-family:monospace;font-size:13px}
        .metrics div{display:flex;justify-content:space-between;padding:3px 0}
        .metrics span:last-child{color:#4ade80}
        .info{background:#7f1d1d;padding:10px;border-radius:8px;margin-bottom:20px;color:#fca5a5}
    </style>
    <div class="header">
        <h1>Dashboard ⚠️ INSECURE</h1>
        <a href="/logout" class="logout-btn">Logout</a>
    </div>
    <div class="info">⚠️ HVGA 480x320 - TCP Klartext - Keine Verschlüsselung</div>
    <div id="cams" class="grid"></div>
    <script>
        let cams = {};
        async function update() {
            try {
                const r = await fetch('/status');
                const d = await r.json();
                const container = document.getElementById('cams');
                if (d.cameras.length === 0 && Object.keys(cams).length === 0) {
                    container.innerHTML = '<p style="color:#666">Warte auf Kamera-Verbindungen...</p>';
                    return;
                }
                d.cameras.forEach(c => {
                    const id = 'cam-' + c.name.replace(/\\W/g, '_');
                    let el = document.getElementById(id);
                    if (!el) {
                        el = document.createElement('div');
                        el.className = 'cam';
                        el.id = id;
                        el.innerHTML = '<h3>' + c.name + '</h3><div class="metrics"></div><img>';
                        container.appendChild(el);
                        cams[c.name] = {el: el, fid: 0};
                        const p = container.querySelector('p');
                        if (p && p.textContent.includes('Warte')) p.remove();
                    }
                    el.querySelector('.metrics').innerHTML =
                        '<div><span>FPS (geglättet):</span><span>' + c.fps.toFixed(1) + '</span></div>' +
                        '<div><span>FPS Min:</span><span>' + c.fps_min.toFixed(1) + '</span></div>' +
                        '<div><span>FPS Max:</span><span>' + c.fps_max.toFixed(1) + '</span></div>' +
                        '<div><span>Standardabweichung:</span><span>' + c.fps_std.toFixed(2) + '</span></div>' +
                        '<div><span>Latenz:</span><span>' + c.latency.toFixed(0) + ' ms</span></div>';
                    const img = el.querySelector('img');
                    if (c.fid !== cams[c.name].fid) {
                        img.src = '/frame/' + c.name + '?t=' + Date.now();
                        cams[c.name].fid = c.fid;
                    }
                });
                Object.keys(cams).forEach(name => {
                    if (!d.cameras.find(c => c.name === name)) {
                        cams[name].el.remove();
                        delete cams[name];
                    }
                });
            } catch(e) { console.error('Update error:', e); }
        }
        setInterval(update, 100);
        update();
    </script>
    """

@app.route("/status")
def status():
    now = time.time()
    cams = []
    with lock:
        for cam in list(frames.keys()):
            if now - last_ts.get(cam, 0) > CAMERA_TIMEOUT:
                frames.pop(cam, None)
                fps.pop(cam, None)
                last_ts.pop(cam, None)
                frame_id.pop(cam, None)
                frame_times.pop(cam, None)
                latency_samples.pop(cam, None)
                esp_offset.pop(cam, None)
                continue
            
            fps_std = 0.0
            fps_min = 0.0
            fps_max = 0.0
            times = frame_times.get(cam, [])
            if len(times) > 10:
                recent = [t for t in times if now - t < 5.0]
                if len(recent) > 10:
                    intervals = [recent[i] - recent[i-1] for i in range(1, len(recent))]
                    instant_fps = [1.0/dt for dt in intervals if dt > 0.001]
                    if len(instant_fps) > 5:
                        sorted_fps = sorted(instant_fps)
                        trim = len(sorted_fps) // 10
                        if trim > 0:
                            trimmed = sorted_fps[trim:-trim]
                        else:
                            trimmed = sorted_fps
                        if trimmed:
                            fps_min = min(trimmed)
                            fps_max = max(trimmed)
                            avg = sum(trimmed) / len(trimmed)
                            variance = sum((x - avg)**2 for x in trimmed) / len(trimmed)
                            fps_std = math.sqrt(variance)
            
            latency = 0.0
            samples = latency_samples.get(cam, [])
            if len(samples) > 5:
                sorted_samples = sorted(samples)
                mid = len(sorted_samples) // 2
                latency = sorted_samples[mid]
            elif samples:
                latency = sum(samples) / len(samples)
            
            cams.append({
                "name": cam,
                "fps": fps.get(cam, 0),
                "fps_min": fps_min,
                "fps_max": fps_max,
                "fps_std": fps_std,
                "latency": latency,
                "fid": frame_id.get(cam, 0)
            })
    return {"cameras": cams}

@app.route("/frame/<cam>")
def frame(cam):
    with lock:
        jpeg = frames.get(cam, b"")
    if jpeg:
        return Response(jpeg, mimetype="image/jpeg")
    return "", 404

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    print("=" * 60)
    print("    INSECURE IoT Video Streaming Server")
    print("  Keine Verschlüsselung, kein Rate-Limiting")
    print("  NUR FÜR TESTZWECKE!")
    print("=" * 60)
    threading.Thread(target=tcp_server, daemon=True).start()
    app.run(host="0.0.0.0", port=HTTP_PORT, threaded=True)
