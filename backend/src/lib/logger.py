import logging

# Configure logger
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)-8s %(message)s'
)
logger = logging.getLogger(__name__)