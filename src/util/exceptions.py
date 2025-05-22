import xml.etree.ElementTree as ET

HTML_NOT_SUPPORTED = Exception("Parsing for html is not supported")
CUSTOM_RESPONSE_NOT_SUPPORTED = Exception("Parsing for custom response is not supported")
PROBLEM_FILE_NOT_FOUND = Exception("Problem file not found")
INVALID_PROBLEM_DEFINITION = Exception("Invalid lon-capa problem definition")


tolerableExceptions = [HTML_NOT_SUPPORTED, CUSTOM_RESPONSE_NOT_SUPPORTED, PROBLEM_FILE_NOT_FOUND, INVALID_PROBLEM_DEFINITION, ET.ParseError]