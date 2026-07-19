try:
    import structlog
except ModuleNotFoundError:
    import logging

    class _LoggerFallback:
        def __init__(self) -> None:
            self._logger = logging.getLogger("meta_ccco_engine")

        def info(self, event_name: str, **kwargs: object) -> None:
            self._logger.info("%s %s", event_name, kwargs)

        def warning(self, event_name: str, **kwargs: object) -> None:
            self._logger.warning("%s %s", event_name, kwargs)

        def error(self, event_name: str, **kwargs: object) -> None:
            self._logger.error("%s %s", event_name, kwargs)

    class _StructlogFallback:
        @staticmethod
        def configure(*_: object, **__: object) -> None:
            logging.basicConfig(level=logging.INFO)

        @staticmethod
        def get_logger() -> _LoggerFallback:
            return _LoggerFallback()

        class processors:
            @staticmethod
            def add_log_level(_: object, __: str, event_dict: dict) -> dict:
                return event_dict

            class TimeStamper:
                def __init__(self, *_: object, **__: object) -> None:
                    pass

                def __call__(self, _: object, __: str, event_dict: dict) -> dict:
                    return event_dict

            class JSONRenderer:
                def __call__(self, _: object, __: str, event_dict: dict) -> str:
                    return str(event_dict)

    structlog = _StructlogFallback()
