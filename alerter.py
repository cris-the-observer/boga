import json
import time
from datetime import datetime

import config


def alert(severity, triggered_groups, observations, transcript, log_file="alerts.log"):
    # Console alert
    print(f"ALERT: {severity}")
    if triggered_groups:
        print(f"Triggered Groups: {', '.join(triggered_groups)}")

    # Log alert
    record = {
        "timestamp": datetime.now().isoformat(),
        "severity": severity,
        "triggered_groups": triggered_groups,
        "observations": observations,
        "transcript": transcript,
    }
    with open(log_file, "a") as f:
        f.write(json.dumps(record) + "\n")

    # GPIO alert
    if severity in {"HIGH", "CRITICAL"}:
        try:
            import RPi.GPIO as GPIO

            # TODO: GPIO setup/cleanup should be managed at application lifecycle level
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            GPIO.setup(config.GPIO_PIN, GPIO.OUT)
            GPIO.output(config.GPIO_PIN, GPIO.HIGH)
            time.sleep(1)
            GPIO.output(config.GPIO_PIN, GPIO.LOW)
            GPIO.cleanup()
        except ImportError:
            pass
