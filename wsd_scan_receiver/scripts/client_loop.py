import os, time

from wsd_scan_receiver.config import Config
from wsd_scan_receiver.logging_config import configure_logging
from wsd_scan_receiver.ws_scan_client import WsScanClientService

open("/tmp/wsclient.pid", "w").write(str(os.getpid()))
configure_logging("INFO")
svc = WsScanClientService(Config.from_env())
svc.start()
while True:
    time.sleep(60)
