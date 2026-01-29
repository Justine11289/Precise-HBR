import requests
import json
from datetime import datetime, timezone

# 確保指向您的 HAPI FHIR 伺服器
BASE_URL = "http://localhost:4004/hapi-fhir-jpaserver/fhir"
# 🚀 請改為您在 4012 頁面看到的那個病人 ID (例如 216303)
TARGET_PID = "1" 

def add_recent_observation(code, value, unit, display):
    # 使用「現在」的時間，確保符合 90 天時效性
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    
    obs_body = {
        "resourceType": "Observation",
        "status": "final",
        "code": {
            "coding": [{"system": "http://loinc.org", "code": code, "display": display}]
        },
        "subject": {"reference": f"Patient/{TARGET_PID}"},
        "effectiveDateTime": now,
        "valueQuantity": {
            "value": value,
            "unit": unit,
            "system": "http://unitsofmeasure.org",
            "code": unit
        }
    }
    
    res = requests.post(f"{BASE_URL}/Observation", json=obs_body)
    if res.status_code == 201:
        print(f"✅ 成功為病人 {TARGET_PID} 增加最近的 {display} ({value} {unit})")

if __name__ == "__main__":
    # 注入 PRECISE-HBR 必備的三大數值
    add_recent_observation("718-7", 11.0, "g/dL", "Hemoglobin")
    add_recent_observation("6690-2", 13.0, "10*9/L", "WBC")
    # 🚀 增加 eGFR (解決您說大部分人都沒有的問題)
    add_recent_observation("33914-3", 70.0, "mL/min/1.73m2", "eGFR")