import xml.etree.ElementTree as ET
from util.context import Context
from parsers.common_parser import *
from flags import RUN_IN_DEV_MODE

def parseReactionResponse(elem: ET.Element, ctx: Context, scope: str) -> None:
    if elem.tag.strip() != "reactionresponse":
        raise Exception("Unexpected invocation of reaction response parser")
    res = dict()

    ansExpr = getAttr(elem, "answer", required=True)
    res["answerValue"] = reduceEmbeddedExprs(ansExpr, ctx, scope=scope)
    res["placeholder"] = "{{answerValue}}" if RUN_IN_DEV_MODE else "use '->' as reaction arrow"
    res["answerId"] = ctx.getAnswerId()
    inputSize = 100
    res["inputSize"] = inputSize

    ctx.setProblem("reactionresponse", res, scope)

def getAttr(elem: ET.Element, attr: str, required=False) -> str|None:
    value = elem.get(attr)
    if required and value is None:
        raise Exception("Required attr {} missing from element {}".format(attr, elem.tag))
    return value