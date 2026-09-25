import logging, os, signal, time
from catalog.loader import CatalogLoader

CATALOG_DIR="/config/catalogs"
logging.basicConfig(level=logging.INFO,format="%(asctime)s %(levelname)s: %(message)s",datefmt="%H:%M:%S")
log=logging.getLogger("ha-reporting")
running=True

def stop(*_):
    global running
    running=False

os.makedirs(CATALOG_DIR,exist_ok=True)
result=CatalogLoader(CATALOG_DIR).load_all()
log.info("------------------------------------------------")
log.info("Catalog discovery complete")
log.info("Loaded: %d",len(result.catalogs))
log.info("Rejected: %d",len(result.errors))
for c in result.catalogs:
    log.info("✓ %s [%s] — %d device(s)",c.name,c.catalog_id,len(c.devices))
for e in result.errors:
    log.error("✗ %s — %s",e.filename,e.message)
if not result.catalogs and not result.errors:
    log.warning("No YAML catalogs found in %s",CATALOG_DIR)
    log.warning("Add *.yaml or *.yml catalog files, then restart HA Reporting.")
log.info("HA Reporting ready.")
signal.signal(signal.SIGTERM,stop)
signal.signal(signal.SIGINT,stop)
while running:
    time.sleep(1)
log.info("HA Reporting stopped.")
