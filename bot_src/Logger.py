import logging
LOGGER = None
def initializeLogger():
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s -[Line:%(lineno)d] - %(message)s ',
        level=logging.INFO
    )

def getLogger():
    global LOGGER
    if LOGGER == None:
        initializeLogger()
        LOGGER = logging.getLogger(__name__)
    return LOGGER