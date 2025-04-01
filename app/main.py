from fastapi import FastAPI, HTTPException
import logging
import json
from datetime import datetime, timezone
from prometheus_fastapi_instrumentator import Instrumentator
import os
import requests
import googlecloudprofiler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("service-a")

CLUSTER_NAME = os.environ.get("CLUSTER_NAME", "unknown-cluster")
SERVICE_B_URL = os.environ.get("SERVICE_B_URL", "http://consumer:8000/")
POD_NAME = os.environ.get("POD_NAME", "unknown-pod")

def log_json(level, component, message, status_code=None):
    log_entry = {
        "level": level,
        "time": datetime.now(timezone.utc).isoformat(),
        "component": component,
        "cluster": CLUSTER_NAME,
        "pod": POD_NAME,
        "message": message
    }
    if status_code is not None:
        log_entry["status_code"] = status_code
    print(json.dumps(log_entry))

app = FastAPI()
Instrumentator().instrument(app).expose(app)

try:
    googlecloudprofiler.start(
        service="servicio-a",
        service_version="v1",
        verbose=2
    )
except (ValueError, NotImplementedError) as exc:
    log_json("warning", "profiler", f"Error initializing Cloud Profiler: {exc}")

@app.get("/")
async def hello():
    log_json("info", "service-a", f"Respondiendo desde Servicio A en el cluster '{CLUSTER_NAME}' (pod: {POD_NAME}).", 200)
    return {"message": f"¡Hola desde el Servicio A en {CLUSTER_NAME}!"}

@app.get("/call-service-b")
async def call_service_b():
    log_json("info", "service-a", f"Intentando llamar a Servicio B desde el cluster '{CLUSTER_NAME}' (pod: {POD_NAME}) a la URL: {SERVICE_B_URL}")

    try:
        response = requests.get(SERVICE_B_URL)
        response.raise_for_status()
        service_b_data = response.json()
        log_json("info", "service-a", f"Respuesta exitosa de Servicio B.", response.status_code)
        return {
            "status": "success",
            "code": response.status_code,
            "data": service_b_data,
            "metadata": {
                "called_service": "B",
                "caller_cluster": CLUSTER_NAME,
                "caller_pod": POD_NAME
            }
        }

    except requests.exceptions.ConnectionError as e:
        log_json("error", "service-a", f"Error al conectar con Servicio B en {SERVICE_B_URL} desde el cluster '{CLUSTER_NAME}' (pod: {POD_NAME}): {e}")
        raise HTTPException(status_code=503, detail=f"No se pudo conectar con Servicio B: {e}")

    except requests.exceptions.HTTPError as e:
        log_json("error", "service-a", f"Error HTTP al llamar a Servicio B (status code: {response.status_code}) desde el cluster '{CLUSTER_NAME}' (pod: {POD_NAME}): {e}")
        raise HTTPException(status_code=response.status_code, detail=f"Error al llamar a Servicio B: {e}")

    except json.JSONDecodeError as e:
        log_json("error", "service-a", f"Error al decodificar la respuesta JSON de Servicio B desde el cluster '{CLUSTER_NAME}' (pod: {POD_NAME}): {e}")
        raise HTTPException(status_code=500, detail="Error al procesar la respuesta de Servicio B")

    except Exception as e:
        log_json("error", "service-a", f"Error inesperado al llamar a Servicio B desde el cluster '{CLUSTER_NAME}' (pod: {POD_NAME}): {e}")
        raise HTTPException(status_code=500, detail="Error inesperado al llamar a Servicio B")

@app.get("/health")
async def health_check():
    log_json("info", "service-a", "Health check llamado desde el cluster '{CLUSTER_NAME}' (pod: {POD_NAME}).", 200)
    return {"status": "ok", "service": "A", "cluster": CLUSTER_NAME, "pod": POD_NAME}