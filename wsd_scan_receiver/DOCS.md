## WSD Scan Receiver (Scan-to-PC)

Dieses Add-on meldet sich im LAN als WSD-Scan-Ziel an ("Web Services for
Devices" / WS-Scan). Multifunktionsgeräte, die "Scan to PC" / "Save to
computer" unterstützen (z. B. Canon TS-Serie, Epson ET-Serie), können dieses
Add-on als Ziel auswählen. Die empfangenen Scans werden direkt nach
`/share/paperless/consume` geschrieben und von Paperless-ngx automatisch
konsumiert (OCR, Verschlagung).

## Bedienung am Drucker (hausfrauen-tauglich)

1. Am Druckerpanel: **Scan → Save to computer / Scan to PC**
2. Das Gerät findet den Receiver automatisch (WS-Discovery). Der angezeigte
   Zielname ist die Option `device_name` (Standard: `Paperless`).
3. Scan starten — die Datei (PDF/JPEG) landet wenige Sekunden später in
   Paperless.

## Einstellungen

Die Settings-Web-UI (Scan-Ticket: Format, Farbe, Auflösung, Zuschnitt) ist über
Ingress erreichbar (HA-Seitenleiste "WSD Scan Settings").

### Add-on-Optionen

- `device_name`: Name, den der Drucker als Scan-Ziel anzeigt
- `scanner_ip`: IP des Scanners (für aktive WS-Eventing-Subscription; nötig,
  wenn Multicast-Discovery nicht zuverlässig funktioniert)
- `subscribe_enabled`: aktive Subscription des `ScanAvailableEvent` beim
  Scanner aktivieren (bei Canon meist erforderlich, damit der Receiver als
  Ziel erscheint)
- `subscribe_interval`: Sekunden zwischen Re-Subscriptions
- `debug`: Roh-SOAP-Payloads nach `/data/debug-dumps` schreiben (Fehleranalyse)
- `log_level`: Debug/Info/Warning/Error

## Netzwerk

Das Add-on läuft mit `host_network: true`, weil WS-Discovery Multicast auf
UDP 3702 braucht. Zusätzlich TCP 5357 (SOAP/DPWS vom Scanner) und TCP 8888
(Settings-UI). Nur in vertrauenswürdigen LANs verwenden — die UI hat keine
Authentifizierung (Ingress über HA-Login ist der sichere Weg).

## Credits

Buildet den vendored Code von
[occino/wsd-scan-receiver](https://github.com/occino/wsd-scan-receiver)
(MIT-Lizenz). WSD-Push-Scannen ist hersteller-sensibel; entwickelt gegen
Epson ET-2750, für Canon experimentell.
