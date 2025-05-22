import xml.etree.ElementTree as ET
from util.context import Context
from parsers.common_parser import *
from typing import (List)
from flags import RUN_IN_DEV_MODE

def parseNumericalResponse(elem: ET.Element, ctx: Context, scope: str) -> dict:

    if elem.tag != "numericalresponse":
        raise Exception("Unexpected invocation of numerical response parser")


    responseDef = dict()
    
    responseDef["answerId"] = ctx.getAnswerId()
    
    responseDef["label"] = elem.text.strip(" \n\t\r") if elem.text is not None else ""
    valueExpr = getAttr(elem, "answer", required=True)
    responseDef["answerValue"] = reduceEmbeddedExprs(valueExpr, ctx, scope=scope)
    responseDef["placeholder"] = "{{answerValue}}" if RUN_IN_DEV_MODE else ""
    answerFormat = getAttr(elem, "format")
    
    responseDef["answerFormat"] = answerFormat

    for child in elem:
        if child.tag == "responseparam":
            parseResponseParam(child, ctx, responseDef, scope)

    #todo: support multiple responses if necessary
    ctx.setProblem("numericalresponse", responseDef, scope)




def parseResponseParam(elem: ET.Element, ctx: Context, responseDef: dict, scope) -> None:
    paramType = getAttr(elem, "type", required=True)
    if paramType == "tolerance":
        tolExpr = getAttr(elem, "default", required=True)
        responseDef["tolerance"] = reduceEmbeddedExprs(tolExpr, ctx, scope=scope)
    elif paramType.startswith("int_range"):
        if "," in paramType:    #a trailing range definition is provided
            value = paramType.split(",")[1]
            if not re.match("(\\d+)|(\\d+-\\d+)", value):
                raise Exception("Invalid significant number range expression in problem ", ctx.problemName)
            sigRange = [int(num) for num in value.split("-")]
        else:   # otherwise look for a default range
            value = getAttr(elem, "default")
            if value is None:
                return 
            if not re.match("(\\d+)|(\\d+,\\d+)", value):
                raise Exception("Invalid significant number range expression in problem ", ctx.problemName)
            sigRange = [int(num) for num in value.split(",")]
        responseDef["sigRange"] =  sigRange
    else:
        raise Exception("Unsupported response param type {} in problem {}".format(paramType, ctx.problemName))



def getAttr(elem: ET.Element, attr: str, required=False) -> str|None:
    value = elem.get(attr)
    if required and value is None:
        raise Exception("Required attr {} missing from element {}".format(attr, elem.tag))
    return value

    









