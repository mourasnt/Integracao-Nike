import sys
import logging

# Try to import loguru; if unavailable, provide a fallback logger API
try:
    from loguru import logger
    _HAS_LOGURU = True
except Exception:
    _HAS_LOGURU = False
    # create a tiny wrapper to approximate loguru interface for debug/info/warning/exception
    class DummyLogger:
        def __init__(self):
            self._logger = logging.getLogger('app')
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
            handler.setFormatter(formatter)
            if not self._logger.handlers:
                self._logger.addHandler(handler)
            self._logger.setLevel(logging.DEBUG)

        def debug(self, *a, **kw):
            self._logger.debug(a[0] % tuple(a[1:]) if a else '')

        def info(self, *a, **kw):
            self._logger.info(a[0] % tuple(a[1:]) if a else '')

        def warning(self, *a, **kw):
            self._logger.warning(a[0] % tuple(a[1:]) if a else '')

        def exception(self, *a, **kw):
            self._logger.exception(a[0] % tuple(a[1:]) if a else '')

    logger = DummyLogger()


# Bridge stdlib logging to loguru (if available)
class InterceptHandler(logging.Handler):
    def emit(self, record):
        try:
            if _HAS_LOGURU:
                # Get corresponding Loguru level if it exists
                level = logger.level(record.levelname).name
                logger.log(level, record.getMessage())
            else:
                logging.getLogger(record.name).handle(record)
        except Exception:
            logging.getLogger(record.name).handle(record)


def configure_logging(level: str = "DEBUG"):
    """Configure loguru and route stdlib logs to it."""
    # If loguru is available, remove existing handlers to avoid duplicate logs
    if _HAS_LOGURU:
        # Remove only handlers that have a loguru-style id attribute to avoid AttributeError
        for h in list(logger._core.handlers.values()):
            hid = getattr(h, 'id', None)
            if hid is not None:
                try:
                    logger.remove(hid)
                except Exception:
                    # Ignore any errors attempting to remove handlers
                    pass

        logger.add(sys.stdout, level=level, backtrace=True, diagnose=True)

    # Intercept the standard logging
    logging.basicConfig(handlers=[InterceptHandler()], level=0)

    # Optional: capture uvicorn loggers
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(name).handlers = [InterceptHandler()]
        logging.getLogger(name).setLevel(logging.DEBUG)

    logger.debug("Logging configured (level=%s, loguru=%s)", level, _HAS_LOGURU)
