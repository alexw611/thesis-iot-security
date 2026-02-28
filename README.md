IoT Camera Security Analysis – Bachelor Thesis
Author
Alexander Werner (Matriculation No. 102206072)
IU Internationale Hochschule
Bachelor of Science – Cyber Security
About This Repository
This repository contains the complete source code developed for the bachelor thesis:
"Sicherheitsanalyse und Haertung eines IoT-Video-Streaming-Systems basierend auf ESP32-CAMs"
(Security Analysis and Hardening of an IoT Video Streaming System Based on ESP32-CAMs)
Up to 98 % of IoT communication remains unencrypted, while regulatory frameworks such as the EU Cyber Resilience Act will mandate security by default from 2027. This thesis investigates the actual performance overhead of lightweight hardening measures on resource-constrained microcontrollers by building a deliberately insecure IoT camera system (Vulnerable by Design), attacking it, hardening it, and measuring the impact.
Repository Structure
thesis-iot-security/
├── README.md
├── requirements.txt
├── system/
│ ├── unsecure.ino
│ ├── unsecure.py
│ ├── data1.py
│ ├── secure.ino
│ ├── secure.py
│ └── data2.py
├── attacks/
│ ├── mitm.py
│ ├── injection.py
│ ├── brute_force.py
│ ├── dos1.py
│ └── dos2.py
└── measurements/
 ├── insecure/
 │ ├── baseline/
 │ ├── dos/
 │ ├── mitm/
 │ ├── injection/
 │ └── bruteforce/
 └── secure/
 ├── baseline/
 ├── dos/
 ├── mitm/
 ├── injection/
 └── bruteforce/
System Architecture
┌──────────────────┐ TCP Port 9000 ┌─────────────────────────┐
│ ESP32-CAM x3 │ ──── Stream ──────→ │ Raspberry Pi 5 │
│ (520 KB RAM) │ │ Flask Dashboard │
│ AES-128 + HMAC │ │ Port 5000 │
└──────────────────┘ │ Account Lockout │
 │ Rate Limiting │
 └─────────────────────────┘
Insecure System
No encryption, no authentication, no rate limiting
TCP stream transmitted in cleartext
Dashboard accessible without login
Hardened System
AES-128-CTR encryption on ESP32-CAMs
HMAC-SHA256 integrity verification on ESP32-CAMs
Bcrypt password hashing on Raspberry Pi
Account lockout (5 failed attempts = 300s lockout) on Raspberry Pi
Rate limiting (30 requests/60s window) on Raspberry Pi
Hardware Requirements
3x ESP32-CAM (AI-Thinker) with OV2640 camera module
1x Raspberry Pi 5 (8 GB RAM)
1x Router (isolated, not connected to the internet)
1x Attacking machine (e.g., MacBook with Python 3.x)
Software Dependencies
pip install flask requests scapy opencv-python numpy Pillow cryptography werkzeug
Ethical Use and Legal Disclaimer
THIS REPOSITORY IS PUBLISHED SOLELY FOR ACADEMIC AND EDUCATIONAL PURPOSES AS PART OF A BACHELOR THESIS AT IU INTERNATIONALE HOCHSCHULE.
Important Notice
All attack scripts were developed and executed exclusively within an isolated lab network that was physically disconnected from the internet.
No production systems, third-party networks, or external devices were targeted at any point during this research.
The Vulnerable by Design system was specifically built for this thesis to demonstrate common IoT security flaws in a controlled environment.
The isolated lab environment is documented in the thesis (Appendix D.3: Ethiknachweis).
By accessing this repository, you agree to the following:
 You will NOT use any of the provided attack scripts against systems you do not own or have explicit written permission to test.
 You will NOT use this code for any illegal, malicious, or unethical purposes.
 You understand that unauthorized access to computer systems is a criminal offense under applicable laws, including but not limited to:
German Criminal Code, Section 202a StGB (Ausspaehen von Daten)
German Criminal Code, Section 303b StGB (Computersabotage)
EU Directive 2013/40/EU on Attacks Against Information Systems
 You assume full legal responsibility for any use or misuse of the code provided in this repository.
The author assumes no liability for:
Any damage caused by the use or misuse of the provided code
Any legal consequences arising from unauthorized use
Any loss of data, service disruption, or security breaches resulting from the application of these tools outside of a controlled lab environment
Attacks Performed
ATTACK
TARGET
INSECURE SYSTEM
HARDENED SYSTEM
Man-in-the-Middle	
TCP stream (port 9000)	
Successful – 25 frames captured	
Blocked (AES-128 + HMAC)
Fake Video Injection	
Dashboard (port 5000)	
Successful – spoofing and injection	
Blocked (HMAC + whitelist)
Brute-Force	
Dashboard login (port 5000)	
Successful – credentials found	
Blocked (lockout + rate limit)
Denial-of-Service	
Dashboard (port 5000)	
Successful – FPS dropped to 0	
Mitigated (rate limiting)
 

Key Findings
Frame rate decrease of 9 to 12 % on two of three cameras after hardening
Latency improvement of 29 to 69 % with 33 % lower standard deviation
Three of four attacks fully blocked after hardening; DoS attack mitigated
The unexpected latency improvement is attributed to bufferbloat mitigation caused by the reduced send rate
The results challenge the assumption that hardening an IoT camera system with resource-constrained microcontrollers necessarily entails significant performance penalties
AI Disclosure
Parts of the source code were generated with the assistance of AI tools (Claude Opus 4.5, Gemini 3 Pro). All AI-generated content was critically reviewed, verified, and modified by the author. Full documentation of AI usage is provided in Appendix E of the thesis, in accordance with the AI usage policy of IU Internationale Hochschule.
License
This project is provided for educational and academic purposes only. No license is granted for commercial use. See the ethical use disclaimer above.
Citation
If you reference this work, please cite:
Werner, A. (2026). Sicherheitsanalyse und Haertung eines IoT-Video-Streaming-Systems basierend auf ESP32-CAMs [Bachelor thesis]. IU Internationale Hochschule.
Contact
For questions regarding this thesis or repository:
[E-Mail-Adresse einfuegen]

Fragen

Erklären

