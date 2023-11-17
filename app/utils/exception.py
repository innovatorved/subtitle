import logging

logger = logging.getLogger(__name__)


def handle_exceptions(func):
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)

        except Exception as exc:
            logger.error(exc)
            raise exc

    return wrapper
