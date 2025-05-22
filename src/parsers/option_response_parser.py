import xml.etree.ElementTree as ET
import uuid
from util.context import Context
from parsers.common_parser import *
from typing import (List)

def parseOptionResponse(elem: ET.Element, ctx: Context, scope: str) -> dict:
    if elem.tag.strip() != "optionresponse":
        raise Exception("Unexpected invocation of option response parser")

    ctx.setProblemField("randomizeDisplayOrder", elem.attrib.get("randomize", "") == "yes") 
    ctx.setMaxDisplayNum(int(elem.attrib.get("max", "-1")))

    foilGroupElem = elem.find("foilgroup")
    
    #todo: handle multiple foil group if necessary
    parseFoilGroup(foilGroupElem, ctx, scope)
    




def parseFoilGroup(elem: ET.Element, ctx: Context, scope) -> None:
    options: List[str] = parseOptions(elem.attrib.get("options", ""))
    if len(options) == 0:
        raise Exception("foil group cannot have empty options")
    res = dict()

    questions = []
    for child in elem:
        if child.tag == "foil":
            parsed = parseFoil(child, ctx, scope)
            parsed["isConceptGroup"] = False
            questions.append(parsed)
        elif child.tag == "conceptgroup":
            questions.append(parseConceptGroup(child, ctx, scope))

    
    res["foils"] = questions
    res["options"] = options
    res["answerId"] = ctx.getAnswerId()
    res["isBlank"] = "false"    #todo: make this configurable if necessary
    res["sort"] = "ascend"
    ctx.setProblem("optionresponse", res, scope)


def parseConceptGroup(elem: ET.Element, ctx: Context, scope: str) -> dict:
    res = dict()
    res["isConceptGroup"] = True
    foils = []
    for child in elem:
        if child.tag == "foil":
            foils.append(parseFoil(child, ctx, scope))
    res["candidates"] = foils
    return res


def parseFoil(elem: ET.Element, ctx: Context, scope: str) -> dict:
    foil = dict()
    value = elem.attrib.get("value", "")
    if len(value) == 0:
        logger.warning("option response foil has empty value in problem {}".format(ctx.problemName))
    
    
    foil["foilName"] = elem.attrib.get("name", str(uuid.uuid4()))
    foil["foilPrompt"] = reduceEmbeddedExprs(extractSubElemAndText(elem), ctx, scope=scope)
    foil["answerValue"] = reduceEmbeddedExprs(value, ctx, scope=scope)

    return foil

    



def parseOptions(rawStr: str) -> List[str]:
    rawStr = rawStr.strip("() ")
    return [elem.strip("'' ") for elem in rawStr.split(",")] + [""]