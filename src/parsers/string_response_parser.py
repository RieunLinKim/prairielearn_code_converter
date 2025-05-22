import xml.etree.ElementTree as ET
from util.context import Context
from parsers.common_parser import *
from flags import RUN_IN_DEV_MODE




def parseStringResponse(elem: ET.Element, ctx: Context, scope: str) -> None:
    if elem.tag.strip() != "stringresponse":
        raise Exception("Unexpected invocation of string response parser")
    res = dict()

    ansExpr = getAttr(elem, "answer", required=True)
    res["answerValue"] = reduceEmbeddedExprs(ansExpr, ctx, scope=scope)
    res["placeholder"] = "{{answerValue}}" if RUN_IN_DEV_MODE else ""
    res["answerId"] = ctx.getAnswerId()
    res["matchType"] = elem.get("type", "cs")   #defaults to case-sensitive matching
    inputSize = 35
    if (txtline := elem.find("textline")) is not None:
        inputSize =  int(txtline.get("size", "35"))
    res["inputSize"] = inputSize

    ctx.setProblem("stringresponse", res, scope)



def getAttr(elem: ET.Element, attr: str, required=False) -> str|None:
    value = elem.get(attr)
    if required and value is None:
        raise Exception("Required attr {} missing from element {}".format(attr, elem.tag))
    return value