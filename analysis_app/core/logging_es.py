import datetime
import logging
import threading
import time

from django.conf import settings

from core.documents.log import LogDocument


class EsLogHandler(logging.Handler):
    """将日志记录批量异步写入 ES 的自定义 Handler。

    - 累积 batch_size 条或每 flush_interval 秒自动 flush 一次（后台线程）；
    - 写 ES 失败静默丢弃，绝不影响主业务流程；
    - 进程退出时调用 close() 会再 flush 一次残留缓冲。
    """

    def __init__(self, level=logging.INFO, batch_size=50, flush_interval=5):
        super().__init__(level=level)
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self._buffer = []
        self._lock = threading.Lock()
        self._timer = threading.Thread(target=self._periodic_flush, daemon=True)
        self._timer.start()

    def emit(self, record):
        try:
            msg = self.format(record)
            doc = {
                "timestamp": datetime.datetime.fromtimestamp(record.created),
                "level": record.levelname,
                "logger_name": record.name,
                "service": "analysis_app",
                "env": getattr(settings, "ENV", "dev"),
                "module": record.name.split(".")[0] if record.name else "",
                "message": msg,
                "exc_info": (
                    self.formatException(record.exc_info) if record.exc_info else None
                ),
            }
            with self._lock:
                self._buffer.append(doc)
                if len(self._buffer) >= self.batch_size:
                    self._flush_locked()
        except Exception:
            self.handleError(record)

    def _periodic_flush(self):
        while True:
            time.sleep(self.flush_interval)
            with self._lock:
                if self._buffer:
                    self._flush_locked()

    def _flush_locked(self):
        if not self._buffer:
            return
        docs = self._buffer[:]
        self._buffer.clear()
        try:
            LogDocument.bulk_save(docs, chunk_size=self.batch_size)
        except Exception:
            # ES 写入失败静默丢弃，避免阻塞主流程
            pass

    def close(self):
        with self._lock:
            self._flush_locked()
        super().close()
