import json, os

from wsd_scan_receiver.config import Config
from wsd_scan_receiver.logging_config import configure_logging
from wsd_scan_receiver.ws_scan_client import (
    WsScanClientService,
    create_scan_job_xml,
    parse_create_scan_job_info,
    retrieve_image_xml,
    service_settings,
)

configure_logging("INFO")
svc = WsScanClientService(Config.from_env())
import time
path = "/data/wsd-subscriptions.json"
deadline = time.monotonic() + 20
while not os.path.exists(path):
    if time.monotonic() > deadline:
        raise SystemExit("keine WSD-Subscription: wsd-subscriptions.json fehlt (Client subscribed noch nicht)")
    time.sleep(2)
subs = json.load(open(path))
sub = list(subs.values())[0]
ticket = svc.config.scan_ticket_store.get() if svc.config.scan_ticket_store else svc.config.scan_ticket

xml = create_scan_job_xml(
    sub["manager_url"],
    scan_identifier=sub["identifier"],
    destination_token=sub["destination_token"],
    device_name=service_settings(svc.config).wsd_device_name,
    from_endpoint=svc.config.endpoint_uuid,
    scan_ticket=ticket,
    input_source="FlatBed",
)
print("[1] CreateScanJob gesendet")
body = svc._post_soap(sub["manager_url"], xml)
print("[2] Antwort:", (body.decode("utf-8", "replace")[:700]) if body else "NONE")
job = parse_create_scan_job_info(body or b"")
if not job:
    raise SystemExit("kein JobId/JobToken")
print("[3] Job:", job.job_id, job.job_token)

resp = svc._post_soap_response(
    sub["manager_url"], retrieve_image_xml(sub["manager_url"], job_id=job.job_id, job_token=job.job_token),
)
if not resp:
    raise SystemExit("RetrieveImage ohne Antwort")
b, ct = resp
print("[4] RetrieveImage:", ct, len(b), "bytes")
svc._store_scan_response(b, ct)
print("[5] gespeichert -> /data/scans, Mover liefert an Paperless")
