import logging
from datetime import datetime, timezone, timedelta


class MoscowTimeFormatter(logging.Formatter):
    def converter(self, timestamp):
        dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        msk_tz = timezone(timedelta(hours=3))
        return dt.astimezone(msk_tz)

    def formatTime(self, record, datefmt=None):
        msk_time = self.converter(record.created)
        if datefmt:
            return msk_time.strftime(datefmt)
        return msk_time.strftime('%Y-%m-%d %H:%M:%S %z')


def setup_logger():
    formatter = MoscowTimeFormatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S %z'
    )

    file_handler = logging.FileHandler("app.log")
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logging.basicConfig(
        level=logging.INFO,
        handlers=[file_handler, console_handler]
    )


def get_logger(name):
    return logging.getLogger(name)