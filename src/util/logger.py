import logging
import os

log_file_name = "lon2prairie.log"
open(log_file_name, "w").close


logging.basicConfig(filename=log_file_name,
                    filemode='a',
                    format='[%(levelname)s] %(message)s',
                    datefmt='%H:%M:%S',
                    level=logging.DEBUG)


logger = logging.getLogger('lon2prairie')