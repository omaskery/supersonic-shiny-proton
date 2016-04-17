import logging
import logging.handlers
import urllib.parse

def start_network_logging(url):
    url = urllib.parse.urlparse(url)
    handler = logging.handlers.SocketHandler(url.hostname, url.port or logging.handlers.DEFAULT_TCP_LOGGING_PORT)
    rootLogger = logging.getLogger()
    rootLogger.addHandler(handler)
