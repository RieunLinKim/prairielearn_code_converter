import xml.etree.ElementTree as ET
import uuid
from util.context import Context
from parsers.common_parser import *
from typing import (List)

def parseRadioButtonResponse(elem: ET.Element, ctx: Context, scope: str) -> None:
    if elem.tag.strip() != "radiobuttonresponse":
        raise Exception("Unexpected invocation of radio button response parser")
    
    res = dict()
    res["randomizeDisplayOrder"] =  elem.attrib.get("randomize", "") == "yes" 
    res["maxDisplayed"] = int(elem.attrib.get("max", "-1"))
    res["answerId"] = ctx.getAnswerId()

    foilGroupElem = elem.find("foilgroup")
    
    #todo: handle multiple foil groups if necessary
    foils = []
    for child in foilGroupElem:
        if child.tag == "foil":
            foils.append(parseFoil(child, ctx, scope))
        
    
    res["foils"] = foils
    
    ctx.setProblem("radiobuttonresponse", res, scope)



def parseFoil(elem: ET.Element, ctx: Context, scope: str) -> dict:
    foil = dict()
    value = elem.attrib.get("value", "")
    if len(value) == 0:
        logger.warning("radio button response foil has empty answer value in problem {}".format(ctx.problemName))
    
    foil["foilName"] = elem.attrib.get("name", str(uuid.uuid4()))
    foil["foilPrompt"] = reduceEmbeddedExprs(extractSubElemAndText(elem), ctx, scope=scope)
    foil["answerValue"] = reduceEmbeddedExprs(value, ctx, scope=scope)

    return foil
