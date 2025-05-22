import xml.etree.ElementTree as ET
from util.context import Context
import re
from perl_translator.lexer import *
from perl_translator.translator import *
from util.logger import logger


def parseProblemHint(elem: ET.Element, ctx: Context, scope: str, precedingText = "") -> None:    
    hintPrompt = "".join(list(elem.itertext()))
    hintPrompt = " ".join(re.split("\\s+", hintPrompt)).strip()
    hintPrompt = reduceEmbeddedExprs(hintPrompt, ctx, scope=scope)
    precedingText = reduceEmbeddedExprs(precedingText, ctx, scope=scope)
    hintFileLinks = []
    for child in elem:
        if child.tag == "a" and (link := child.get("href")) != None:
            hintFileLinks.append(link)

    ctx.setHint(precedingText, hintPrompt, hintFileLinks)

# switch a img element to prairielearn counterpart in-place
def parseImage(elem: ET.Element) -> None:
    tag = elem.tag
    if tag != "img":
        for child in elem:
            parseImage(child)
    
    else:
        elem.tag = "pl-figure"
        srcLink = elem.get("src")
        if srcLink is None or len(srcLink.split("/")) == 0:
            raise Exception("img element has invalid src")
        for k in list(elem.attrib.keys()):
            elem.attrib.pop(k)
        
        elem.set("file-name", srcLink.split("/")[-1])
        elem.set("directory", "clientFilesQuestion")



def parseScript(elem: ET.Element, ctx: Context, scope: str) -> None:
    script = elem.text

    charMap = {
        "&lt;": "<",
        "&gt;": ">",
        "&amp;": "&",
    }

    for k, v in charMap.items():
        script = script.replace(k, v)    
    pyScript = pythonize(script)
    ctx.setScript(scope, pyScript)



    
    

def extractSubElemAndText(elem: ET.Element) -> str:
    start = False
    res = "" 
    if elem.find("startouttext") is not None and elem.find("endouttext") is not None:
        for child in elem:

            if child.tag == "startouttext":
                start = True
                res = "" if child.tail is None else child.tail
            elif child.tag == "endouttext":
                break
            elif len(list(child)) == 0 and child.text is None and child.tag not in ['br', 'pl-figure']: #ignore self closing elems
                continue
            elif start:
                res += ET.tostring(child, encoding="unicode")
    else:
        res = elem.text if elem.text is not None else ""
        for child in elem:
            if len(list(child)) == 0 and child.text is None and child.tag not in ['br', 'pl-figure']: #ignore self closing elems
                continue
            res += ET.tostring(child, encoding="unicode")
    return res

# convert lon-capa chem tag text into plain html in-place 
def parseChemEquation(elem: ET.Element):
    if elem.tag != "chem":
        for child in elem:
            parseChemEquation(child)
    else:
        equation = elem.text 
        if equation is None:
            return 
        res = []
        i = 0
        startReactant = True
        while i<len(equation):
            chr = equation[i]
            if chr == " ":
                res.append("\u00A0")
                i += 1
                
            elif chr.isalpha() or chr in "[]()/": #the usage of / seems to be only for giving a wrong example of coefficient
                startReactant = False
                res.append(chr)
                i += 1
            elif chr == "^":
                startReactant = False
                i += 1
                rp = i
                while rp < len(equation) and (equation[rp].isdigit() or equation[rp] in "+-"):
                    rp += 1
                supText = equation[i:rp]
                supText = supText.replace("+", "\u002B")
                supText = supText.replace("-", "\u2212")
                res.append("<sup>{}</sup>".format(supText))
                i = rp 
            elif chr == "+":
                res.append("\u002B")
                i += 1
                startReactant = True
            elif chr == "-":
                if i+1<len(equation) and equation[i+1] == ">":
                    res.append("\u2192")
                    i += 2
                    startReactant = True
                else:
                   res.append("\u2212")
                   i += 1
                
            elif chr.isdigit():
                rp = i
                while rp<len(equation) and equation[rp].isdigit():
                    rp += 1
                if startReactant:
                    res.append(equation[i:rp])
                else:
                    res.append("<sub>{}</sub>".format(equation[i:rp]))
                i = rp
                startReactant = False
            else:
                # raise Exception("invalid equation syntax for ", equation,  " at postion ", str(i))
                res.append(chr)
                i += 1
        inner = "".join(res)
        res = ET.fromstring("<text>" + inner + "</text>")
        res.set("style", 'font-family: Times New Roman, Times, serif;')
        elem.text = ""

        elem.append(res)

            
# extract, translate, and name an embedded perl expression
# return text with embedded expr replaced with a unique expression ID
# currently only support plain ID, arrayID[idxID] arrayID[int] expressions
def reduceEmbeddedExprs(text: str, ctx: Context, scope: str, inText: bool = False) -> str:

    text = text.replace("&amp;", "&")

    identifierRegex = "\\$[a-zA-Z_][a-zA-Z0-9_]*"
    arrayIndexingRegex = "^{}\\[({}|\\d+)\\]".format(identifierRegex, identifierRegex)
    result = []
    
    visibleVars = ctx.getVisibleVariablesNames(scope)
    def isInScope(varName):
        return varName in visibleVars

    i = 0
    while i < len(text):
        chr = text[i]
        if not chr == "$":
            result.append(chr)
            i += 1
        else:
            if (matched := re.match(arrayIndexingRegex, text[i:])):
                matched = matched.group(0)
                arrayName, idxExpr = matched.split("[")
                arrayName = "vector_" + arrayName[1:]
                
                if not isInScope(arrayName):
                    logger.warning("array ID %s not found when reducing array indexing expression under scope %s" % (arrayName, scope))
                    result.append(matched)
                    i += len(matched)
                    continue
                
                
                if idxExpr[0].isdigit():
                    idxSym = str(int(idxExpr[:-1])) 
                else:
                    idxSym = "scalar_" + idxExpr[1:-1]
                    if not isInScope(idxSym):
                        logger.warning("index ID %s not found when reducing array indexing expression under scope %s" % (arrayName, scope))
                        result.append(matched)
                        i += len(matched)
                        continue
                
                expr = "{}[{}]".format(arrayName, idxSym)
                exprName = ctx.addReference(scope, expr)
                if inText:
                    form = "{{{params.generatedVars." + scope + "." +exprName+"}}}"
                else:
                    form = "{{"+exprName+"}}"
                result.append(form)
                i += len(matched)
            elif (matched := re.match(identifierRegex, text[i:])):
                matched = matched.group(0)
                varName = "scalar_" + matched[1:]
                if not isInScope(varName):
                    logger.warning("scalar ID %s not found when reducing expression under scope %s" % (varName, scope))
                    result.append(matched)
                    i += len(matched)
                    continue
                exprName = ctx.addReference(scope, varName)
                if inText:
                    form = "{{{params.generatedVars." + scope + "." + exprName+"}}}"
                else:
                    form = "{{"+exprName+"}}"
                result.append(form)
                i += len(matched)
            else:
                result.append(chr)
                i += 1
             
    return  "".join(result)


def refactorLatexExprs(elem: ET.Element) -> None:
    if elem.tag != "m" or elem.get("display","")!="jsMath":
        for child in elem:
            refactorLatexExprs(child)
    
    else:
        expression = elem.text 
        if not expression.startswith("$") or not expression.endswith("$"):
            return
        expression = expression.strip("$ ")
        if expression.startswith("\\(") and expression.endswith("\\)"):
            expression = expression[3:-2]
        elem.text = "$"+ expression +"$"
        


            
        