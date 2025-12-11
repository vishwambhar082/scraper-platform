from __future__ import annotations

import json
from typing import Any, Dict, Iterable

from src.common.logging_utils import get_logger

log = get_logger("etl-kafka")

try:
    from confluent_kafka import Producer  # type: ignore[import]
except Exception:  # pragma: no cover
    Producer = None  # type: ignore[assignment]


def produce_to_kafka(
    topic: str,
    messages: Iterable[Dict[str, Any]],
    config: Dict[str, Any],
) -> int:
    """
    Produce messages to Kafka using confluent-kafka.

    Raises RuntimeError if confluent-kafka is not installed.
    """
    if Producer is None:
        raise RuntimeError("confluent-kafka not installed")

    producer = Producer(config)
    count = 0

    def _delivery(err, msg):  # pragma: no cover (callbacks hard to test)
        if err is not None:
            log.error("Kafka delivery failed", extra={"error": str(err)})
        else:
            log.debug("Kafka message delivered", extra={"topic": msg.topic(), "partition": msg.partition()})

    for m in messages:
        payload = json.dumps(m, default=str).encode("utf-8")
        producer.produce(topic, payload, callback=_delivery)
        count += 1

    producer.flush()
    log.info("Produced Kafka messages", extra={"topic": topic, "count": count})
    return count


def publish_records(
    topic: str,
    records: Iterable[Dict[str, Any]],
    dry_run: bool = False,
) -> int:
    """
    Backward-compatible wrapper for produce_to_kafka.

    Uses default Kafka config from environment variables.
    """
    import os

    try:
        rows_list = list(records)
    except Exception as exc:
        log.error("Failed to materialize records for Kafka", extra={"error": str(exc)})
        return 0

    if dry_run:
        log.info("Kafka dry-run: topic=%s, messages=%d", topic, len(rows_list))
        return len(rows_list)

    # Build config from env vars or use defaults
    config = {
        "bootstrap.servers": os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
    }
    # Add optional auth config
    if os.getenv("KAFKA_SASL_USERNAME"):
        config.update({
            "security.protocol": "SASL_SSL",
            "sasl.mechanism": "PLAIN",
            "sasl.username": os.getenv("KAFKA_SASL_USERNAME"),
            "sasl.password": os.getenv("KAFKA_SASL_PASSWORD", ""),
        })

    return produce_to_kafka(topic, rows_list, config)


__all__ = ["produce_to_kafka", "publish_records"]
