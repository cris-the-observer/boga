import json
import time
from datetime import datetime


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
    if severity in ["HIGH", "CRITICAL"]:
        try:
            import RPi.GPIO as GPIO

            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            GPIO.setup(18, GPIO.OUT)
            GPIO.output(18, GPIO.HIGH)
            time.sleep(1)  # mock delay or actual delay
            GPIO.output(18, GPIO.LOW)
            GPIO.cleanup()
        except ImportError:
            pass
