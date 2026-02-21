import json
import logging
import time
from datetime import datetime

import config

log = logging.getLogger(__name__)


def alert(severity, triggered_groups, observations, transcript, log_file="alerts.log"):
    # Console alert
    log.warning("!!! ALERT: %s — groups: %s !!!", severity, ", ".join(triggered_groups) or "(none)")
    for obs in observations:
        log.warning("  observation: %s", obs)

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
    log.info("Alert written to %s", log_file)

    # GPIO alert
    if severity in {"HIGH", "CRITICAL"}:
        try:
            import RPi.GPIO as GPIO

            log.info("Pulsing GPIO pin %d for %s alert", config.GPIO_PIN, severity)
            # TODO: GPIO setup/cleanup should be managed at application lifecycle level
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            GPIO.setup(config.GPIO_PIN, GPIO.OUT)
            GPIO.output(config.GPIO_PIN, GPIO.HIGH)
            time.sleep(1)
            GPIO.output(config.GPIO_PIN, GPIO.LOW)
            GPIO.cleanup()
            log.info("GPIO pin %d pulse complete", config.GPIO_PIN)
        except ImportError:
            log.info("RPi.GPIO not available — skipping GPIO alert")
