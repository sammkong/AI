# ============================================================
# 구조화 로깅 유틸리티
#
# 모든 로그를 JSON 한 줄로 출력 → 로그 집계 도구(ELK, Loki 등) 연동 용이
#
# 사용 예)
#   log = get_logger("consumer.classify")
#   log.info("received",  queue="q.2ai.classify", request_id="req-001", emailId="e-1")
#   log.info("processed", queue="q.2ai.classify", request_id="req-001",
#            emailId="e-1", success=True, elapsed_ms=123.4)
#   log.error("failed",   queue="q.2ai.classify", request_id="req-001",
#             emailId="e-1", success=False, error="timeout")
# ============================================================

import json
import logging
import sys
from datetime import datetime, timezone


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base = {
            "ts":     _utc_now(),
            "level":  record.levelname,
            "logger": record.name,
            "msg":    record.getMessage(),
        }
        # structured 필드는 record.struct_fields 에 첨부
        extra = getattr(record, "struct_fields", {})
        return json.dumps({**base, **extra}, ensure_ascii=False)


class StructuredLogger:
    """
    JSON 구조화 로거.
    표준 Python logger 위에 struct_fields 를 주입하는 thin wrapper.
    """

    def __init__(self, name: str, level: int = logging.INFO):
        self._logger = logging.getLogger(name)
        if not self._logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(_JsonFormatter())
            self._logger.addHandler(handler)
            self._logger.propagate = False
        self._logger.setLevel(level)

    def _emit(self, level: int, msg: str, **fields) -> None:
        record = self._logger.makeRecord(
            name=self._logger.name,
            level=level,
            fn="",
            lno=0,
            msg=msg,
            args=(),
            exc_info=None,
        )
        record.struct_fields = fields  # type: ignore[attr-defined]
        self._logger.handle(record)

    def info(self, msg: str, **fields) -> None:
        self._emit(logging.INFO, msg, **fields)

    def warning(self, msg: str, **fields) -> None:
        self._emit(logging.WARNING, msg, **fields)

    def error(self, msg: str, **fields) -> None:
        self._emit(logging.ERROR, msg, **fields)

    def debug(self, msg: str, **fields) -> None:
        self._emit(logging.DEBUG, msg, **fields)


def get_logger(name: str, level: int = logging.INFO) -> StructuredLogger:
    return StructuredLogger(name, level)
