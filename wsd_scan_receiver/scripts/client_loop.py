import os, time

from wsd_scan_receiver.config import Config
from wsd_scan_receiver.logging_config import configure_logging
from wsd_scan_receiver.ws_scan_client import (
    DiscoveredScanDevice,
    WsScanClientService,
)

open("/tmp/wsclient.pid", "w").write(str(os.getpid()))
configure_logging("INFO")
cfg = Config.from_env()
svc = WsScanClientService(cfg)
svc.start()

# Multicast probe/send is unreliable on HAOS hosts, so bootstrap the WSD
# subscription directly via HTTP against the scanner's scan service and keep
# it renewed every interval (subscription expires after ~300s).
scanner_ip = cfg.scanner_ip
device = None
if scanner_ip:
    device = DiscoveredScanDevice(
        endpoint="urn:uuid:00000000-1000-8000-7438b78df59b",
        types="wscn:ScanDeviceType",
        xaddrs=(f"http://{scanner_ip}/wsd/scanservice.cgi",),
        peer=f"{scanner_ip}:80",
    )
interval = max(cfg.wsd_subscribe_interval_seconds, 60)
while True:
    if device is not None:
        try:
            svc._subscribe_to_device(device)
        except Exception:
            pass
    time.sleep(interval)
