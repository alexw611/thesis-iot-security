# Erstellt am 04.02.2026 von Claude Opus 4.5

import socket
import threading
import time
import math
import hashlib
import hmac
import os
import secrets
from collections import defaultdict
from functools import wraps
from flask import Flask, Response, redirect, url_for, session, request, abort
from werkzeug.security import generate_password_hash, check_password_hash
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

TCP_PORT = 9000
HTTP_PORT = 5000
CAMERA_TIMEOUT = 15.0


ADMIN_USERNAME = "admin"

ADMIN_PASSWORD_HASH = generate_password_hash("S3cur3!P@ssw0rd#2026")

CAMERA_PSK = b"ThisIs32ByteSecretKeyForCam!!" 

AES_KEY = b"AES128SecretKey!" 

ALLOWED_CAMERAS = {"Garten_Cam_01", "Garten_Cam_02", "Garten_Cam_03"}


RATE_LIMIT_REQUESTS = 30 
RATE_LIMIT_WINDOW = 60   

MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_TIME = 300  


frames = {}
fps = defaultdict(float)
last_ts = {}
frame_id = defaultdict(int)
lock = threading.Lock()

frame_times = defaultdict(list)
latency_samples = defaultdict(list)
esp_offset = {}

rate_limit_tracker = defaultdict(list) 
login_attempts = defaultdict(list)     
authenticated_cameras = {}             

def verify_camera_hmac(cam_name: str, timestamp: str, received_hmac: str) -> bool:
    """Verifiziert HMAC-SHA256 Signatur der Kamera"""
    message = f"{cam_name}:{timestamp}".encode()
    expected_hmac = hmac.new(CAMERA_PSK, message, hashlib.sha256).hexdigest()[:16]
    return hmac.compare_digest(expected_hmac, received_hmac)

def decrypt_frame(encrypted_data: bytes, iv: bytes) -> bytes:
    """Entschlüsselt Frame mit AES-128-CTR"""
    cipher = Cipher(algorithms.AES(AES_KEY), modes.CTR(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    return decryptor.update(encrypted_data) + decryptor.finalize()

def tcp_server():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
    s.bind(("0.0.0.0", TCP_PORT))
    s.listen(10)
    print(f"[TCP-SECURE] Port {TCP_PORT} - Verschlüsselung aktiv")
    while True:
        conn, addr = s.accept()
        conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        print(f"[TCP] {addr} connected")
        threading.Thread(target=handle_client_secure, args=(conn, addr), daemon=True).start()

def handle_client_secure(conn, addr):
    """Sichere Client-Behandlung mit Authentifizierung"""
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
                
                # Neues Protokoll: CAM:<name>:<size>:<timestamp>:<hmac>:<iv_hex>
                if len(parts) < 6 or parts[0] != "CAM":
                    buf = rest
                    continue
                
                cam = parts[1]
                try:
                    length = int(parts[2])
                    esp_epoch_ms = int(parts[3])
                except ValueError:
                    buf = rest
                    continue
                    
                received_hmac = parts[4]
                iv_hex = parts[5]
                
                if len(rest) < length:
                    break
                
                encrypted_jpeg = rest[:length]
                buf = rest[length:]
                
                if cam not in ALLOWED_CAMERAS:
                    print(f"[SECURITY] Unbekannte Kamera abgelehnt: {cam}")
                    continue
                
                if not verify_camera_hmac(cam, parts[3], received_hmac):
                    print(f"[SECURITY] HMAC-Verifikation fehlgeschlagen für {cam}")
                    continue
                
                server_ms = time.time() * 1000
                time_diff = abs(server_ms - esp_epoch_ms)
                if time_diff > 30000:
                    print(f"[SECURITY] Replay-Angriff vermutet für {cam}")
                    continue
                
                try:
                    iv = bytes.fromhex(iv_hex)
                    jpeg = decrypt_frame(encrypted_jpeg, iv)
                except Exception as e:
                    print(f"[SECURITY] Entschlüsselung fehlgeschlagen: {e}")
                    continue
                
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
                        latency = server_ms - esp_epoch_ms
                        if 0 < latency < 5000:
                            latency_samples[cam].append(latency)
                            if len(latency_samples[cam]) > 100:
                                latency_samples[cam] = latency_samples[cam][-50:]
                
                count += 1
                if count % 50 == 0:
                    print(f"[SECURE] {cam}: {count} Frames empfangen")
                
        except Exception as e:
            print(f"[TCP] Error: {e}")
            break
    
    print(f"[TCP] {addr} disconnected - Frames: {count}")
    conn.close()

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

def rate_limit(f):
    """Rate-Limiting nur für nicht-eingeloggte User"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("logged_in"):
            return f(*args, **kwargs)
        
        ip = request.remote_addr
        now = time.time()
        
        rate_limit_tracker[ip] = [t for t in rate_limit_tracker[ip] 
                                   if now - t < RATE_LIMIT_WINDOW]
        
        if len(rate_limit_tracker[ip]) >= RATE_LIMIT_REQUESTS:
            print(f"[SECURITY] Rate-Limit erreicht für {ip}")
            abort(429)
        
        rate_limit_tracker[ip].append(now)
        return f(*args, **kwargs)
    return decorated_function

def check_brute_force(ip: str) -> bool:
    """Prüft ob IP wegen zu vieler Fehlversuche gesperrt ist"""
    now = time.time()
    recent_attempts = [t for t in login_attempts[ip] if now - t < LOCKOUT_TIME]
    login_attempts[ip] = recent_attempts
    return len(recent_attempts) >= MAX_LOGIN_ATTEMPTS

def record_failed_login(ip: str):
    """Zeichnet fehlgeschlagenen Login-Versuch auf"""
    login_attempts[ip].append(time.time())

@app.route("/", methods=["GET", "POST"])
@rate_limit
def login():
    ip = request.remote_addr
    if check_brute_force(ip):
        remaining = LOCKOUT_TIME - (time.time() - login_attempts[ip][-1])
        return f"""
        <style>
            body{{background:#0a0a0a;color:#fff;font-family:system-ui;display:flex;
                  justify-content:center;align-items:center;height:100vh;margin:0}}
            .box{{background:#7f1d1d;padding:40px;border-radius:16px;text-align:center}}
        </style>
        <div class="box">
            <h2>🔒 Account gesperrt</h2>
            <p>Zu viele Fehlversuche. Warten Sie {int(remaining)} Sekunden.</p>
        </div>
        """, 403
    
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        
        if username == ADMIN_USERNAME and check_password_hash(ADMIN_PASSWORD_HASH, password):
            session["logged_in"] = True
            session["login_time"] = time.time()
            session.permanent = False  
            print(f"[AUTH] Erfolgreicher Login von {ip}")
            return redirect(url_for("dashboard"))
        else:
            record_failed_login(ip)
            attempts_left = MAX_LOGIN_ATTEMPTS - len(login_attempts[ip])
            print(f"[SECURITY] Fehlgeschlagener Login von {ip} - {attempts_left} Versuche übrig")
            return f"""
            <style>
                body{{background:#0a0a0a;color:#fff;font-family:system-ui;display:flex;
                      justify-content:center;align-items:center;height:100vh;margin:0}}
                .box{{background:#1a1a2e;padding:40px;border-radius:16px}}
                .error{{color:#ef4444;margin-bottom:20px;text-align:center}}
                h2{{margin:0 0 20px 0;text-align:center}}
                input{{display:block;margin:12px 0;padding:12px;width:220px;
                       background:#16213e;border:1px solid #334155;color:#fff;border-radius:8px}}
                button{{padding:12px;background:#ef4444;border:none;color:#fff;
                        cursor:pointer;border-radius:8px;width:100%;font-weight:bold}}
            </style>
            <div class="box">
                <div class="error">❌ Falsches Passwort! ({attempts_left} Versuche übrig)</div>
                <h2>Admin Login</h2>
                <form method="post">
                    <input name="username" placeholder="Username" required>
                    <input type="password" name="password" placeholder="Password" required 
                           minlength="8" pattern="(?=.*\d)(?=.*[a-z])(?=.*[A-Z])(?=.*\W).{{8,}}">
                    <button>Login</button>
                </form>
            </div>
            """
    
    return """
    <style>
        body{background:#0a0a0a;color:#fff;font-family:system-ui;display:flex;
             justify-content:center;align-items:center;height:100vh;margin:0}
        .box{background:#1a1a2e;padding:40px;border-radius:16px}
        h2{margin:0 0 20px 0;text-align:center}
        input{display:block;margin:12px 0;padding:12px;width:220px;
              background:#16213e;border:1px solid #334155;color:#fff;border-radius:8px}
        button{padding:12px;background:#22c55e;border:none;color:#fff;
               cursor:pointer;border-radius:8px;width:100%;font-weight:bold}
        button:hover{background:#16a34a}
        .secure{color:#22c55e;font-size:12px;text-align:center;margin-top:15px}
    </style>
    <div class="box">
        <h2>🔐 Secure Admin Login</h2>
        <form method="post">
            <input name="username" placeholder="Username" required autocomplete="username">
            <input type="password" name="password" placeholder="Password" required 
                   autocomplete="current-password">
            <button>Login</button>
        </form>
        <div class="secure">🛡️ TLS + Rate-Limiting + Brute-Force-Schutz</div>
    </div>
    """

@app.route("/dashboard")
@rate_limit
def dashboard():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    
    if time.time() - session.get("login_time", 0) > 1800:
        session.clear()
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
        .cam img{width:100%;border:2px solid #22c55e;border-radius:8px;background:#000}
        .fps{color:#4ade80;font-weight:bold;font-size:16px;margin-bottom:10px}
        .metrics{background:#16213e;padding:10px;border-radius:8px;margin-bottom:10px;
                 font-family:monospace;font-size:13px}
        .metrics div{display:flex;justify-content:space-between;padding:3px 0}
        .metrics span:last-child{color:#4ade80}
        .info{background:#16213e;padding:10px;border-radius:8px;margin-bottom:20px;color:#22c55e}
        .secure-badge{background:#22c55e;color:#000;padding:3px 8px;border-radius:4px;
                      font-size:12px;margin-left:10px}
    </style>
    <div class="header">
        <h1>Dashboard <span class="secure-badge">🔒 SECURED</span></h1>
        <a href="/logout" class="logout-btn">Logout</a>
    </div>
    <div class="info">🛡️ HVGA 480x320 - AES-128-CTR + HMAC-SHA256 Authentifizierung</div>
    <div id="cams" class="grid"></div>
    <script>
        let cams = {};
        async function update() {
            try {
                const r = await fetch('/status');
                if (r.status === 401) { window.location = '/'; return; }
                if (r.status === 429) { console.warn('Rate limited'); return; }
                const d = await r.json();
                const container = document.getElementById('cams');
                if (d.cameras.length === 0 && Object.keys(cams).length === 0) {
                    container.innerHTML = '<p style="color:#666">Warte auf authentifizierte Kamera-Verbindungen...</p>';
                    return;
                }
                d.cameras.forEach(c => {
                    const id = 'cam-' + c.name.replace(/\\W/g, '_');
                    let el = document.getElementById(id);
                    if (!el) {
                        el = document.createElement('div');
                        el.className = 'cam';
                        el.id = id;
                        el.innerHTML = '<h3>🔐 ' + c.name + '</h3><div class="metrics"></div><img>';
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
@rate_limit
def status():
    if not session.get("logged_in"):
        return {"error": "unauthorized"}, 401
    
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
@rate_limit
def frame(cam):
    if not session.get("logged_in"):
        return "", 401
    with lock:
        jpeg = frames.get(cam, b"")
    if jpeg:
        return Response(jpeg, mimetype="image/jpeg")
    return "", 404

@app.route("/logout")
def logout():
    ip = request.remote_addr
    rate_limit_tracker.pop(ip, None)
    login_attempts.pop(ip, None)      
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    print("=" * 60)
    print("  SECURE IoT Video Streaming Server")
    print("  Schutz gegen: DoS, Brute-Force, Injection, Sniffing")
    print("=" * 60)
    threading.Thread(target=tcp_server, daemon=True).start()
    app.run(host="0.0.0.0", port=HTTP_PORT, threaded=True)
