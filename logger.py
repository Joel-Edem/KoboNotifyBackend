import logging
import sys
import enum


class Colors(enum.Enum):
    WHITE = "\033[0m"
    RED = "\033[91m"
    PINK = "\033[35m"
    GREEN = "\u001b[32m"
    YELLOW = "\u001b[33m"
    CYAN = "\033[36m"
    BLUE = "\033[34m"
    H = "\033[34m"

    @classmethod
    def from_name(cls, color: str):
        color = color.lower()
        if color == 'red':
            return cls.RED
        elif color == 'pink':
            return cls.PINK
        elif color == 'green':
            return cls.GREEN
        elif color == 'yellow':
            return cls.YELLOW
        elif color == 'blue':
            return cls.BLUE
        elif color == 'cyan':
            return cls.CYAN
        elif color == 'h':
            return cls.H
        else:
            return cls.WHITE


class ColorFormatter(logging.Formatter):
    def format(self, record):
        if isinstance(record.args, tuple):
            args = record.args
            record.args = {"color": "", "location":""}
            if len(args):
                record.args['color'] = args[0]
            if len(args) > 1:
                record.args["location"] = args[1]

        color = record.args.get('color', "")
        location = record.args.get('location', "")
        color_val = (color.value if isinstance(color, Colors) else Colors.from_name(color).value) if color else ""
        record.color = color_val
        record.location = f"{location}:" if location else location
        return super().format(record)


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = ColorFormatter("%(color)s%(location)s %(message)s")
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
ch.setFormatter(formatter)
logger.addHandler(ch)

if __name__ == "__main__":
    logger.debug("test message", {"color": 'cyan', "location": "messages"})
