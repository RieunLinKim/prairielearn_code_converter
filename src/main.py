import xml.etree.ElementTree as ET
from util.context import Context
from parsers.option_response_parser import parseOptionResponse
from parsers.numerical_response_parser import parseNumericalResponse
from parsers.rank_response_parser import parseRankResponse
from parsers.string_response_parser import parseStringResponse
from parsers.radio_button_response_parser import parseRadioButtonResponse
from parsers.reaction_response_parser import parseReactionResponse
from parsers.common_parser import *
import json
import os
from pathlib import Path
from perl_translator.lexer import *
import shutil
from util.exceptions import *
from util.execution_manager import ExecutionManager
from util.logger import logger

# _source_folder = "chem104"
_source_folder = "sample_questions"

# parser for elements outside of question elements
commonTargets = {
    "script": parseScript,
    "hintgroup": parseProblemHint,
}

problemTargets = {
    "stringresponse": parseStringResponse,
    "radiobuttonresponse": parseRadioButtonResponse,
    "customresponse": None,
    "reactionresponse": parseReactionResponse,
    "optionresponse": parseOptionResponse,
    "rankresponse": parseRankResponse,
    "numericalresponse": parseNumericalResponse,
    "formularesponse": None,
}

# generate target prairielearn files from lon-capa definitions
def genTarget(ctx: Context) -> None:
    root = ctx.xmlRoot
    parseImage(root)
    parseChemEquation(root)
    refactorLatexExprs(root)
    walkXmlTree(root, ctx)
    ctx.moveStaticResources()
    ctx.genTargetResource()


# dfs the xml tree and search for target tags
def walkXmlTree(root: ET.Element, ctx: Context) -> None:

    notHTML = ["script", "part", "problem", "startouttext", "endouttext", "starttext", "endtext", "allow", "parameter", "root"]
    precedingMarkup = "" if root.text is None else root.text

    stack = [root]
    scopes = [ExecutionManager.SCOPE_DEFAULT]
    ctx.setScript(ExecutionManager.SCOPE_DEFAULT, "")

    while len(stack) > 0:
        elem = stack.pop()

        if type(elem) == str:
            if elem == "pop_scope":
                precedingMarkup = reduceEmbeddedExprs(precedingMarkup, ctx, scopes[-1], inText=True)
                scopes.pop()
            else:
                precedingMarkup += elem 
            continue

        tag = elem.tag 

        if tag == "script":
            parseScript(elem, ctx, scopes[-1])
        
        elif tag == "hintgroup":
            parseProblemHint(elem, ctx, scopes[-1], precedingMarkup)
            precedingMarkup = "" if elem.tail is None else elem.tail

        elif tag in problemTargets:
            parseProblem(elem, ctx, precedingMarkup, scopes[-1])
            precedingMarkup = "" if elem.tail is None else elem.tail

        else:

            # try explore children
            children = [child for child in elem]
            
            if tag == "part":
                scopeId = "scope_" + elem.get("id")
                if scopeId in scopes:
                    raise Exception("Duplicate part id in problem")
                scopes.append(scopeId)
                ctx.setScript(scopeId, "")
                children.append("pop_scope")

            children.reverse()

            tail = ""
            # some elems are not html
            if not tag in notHTML:
                attrs = " ".join('{}="{}"'.format(k, v) for k, v in elem.attrib.items())
                precedingMarkup += "<{} {}>".format(tag, attrs)
                tail = "</{}>".format(tag)

            if elem.text is not None:
                precedingMarkup += elem.text
                
            if elem.tail is not None: 
                tail = tail + elem.tail 
            
            children = [tail] + children # hacky, adds in succeeding text
            stack += children
    
    if precedingMarkup is not None:
        ctx._problemData["tail"] =  reduceEmbeddedExprs(precedingMarkup, ctx, scopes[-1], inText=True)


def parseProblem(elem: ET.Element, ctx: Context, prompt: str, scope: str) -> None:
    reduced = reduceEmbeddedExprs(prompt, ctx, inText=True, scope=scope)
    ctx.setPrompt(reduced)
    tag = elem.tag
    parser = problemTargets.get(tag)

    if parser is not None:
        parser(elem, ctx, scope)
    else:
        logger.warning("parser not implemented for %s" % tag)

    if (hint := elem.find("hintgroup")) is not None:
        parseProblemHint(hint, ctx, scope)




        
def cleanFolder(folder):
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)    # remove file
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)    # remove folder
        except Exception as e:
            logger.warning('Failed to clean folder %s with error %s' % (file_path, e))



if __name__ == "__main__":
    problemNames = set()
    problemIDs = []

    Path("out/questions").mkdir(parents=True, exist_ok=True)
    cleanFolder("out/questions")

    curPath = str(Path(__file__).parent.resolve())  # get the absolute path of the parent directory of current file
    fileDirs = []
    for questionDir in os.listdir(curPath+"/../" + _source_folder):
        path = _source_folder + "/" + questionDir
        # if questionDir not in ["10"]:
        #     continue
        if not os.path.isdir(path):
            continue
        fileDirs.append(path)
    fileDirs = sorted(fileDirs)
    for path in fileDirs:
        logger.info("start processing " + path)
        try:
            ctx = Context(path)
            problemName = "".join(ctx.problemName.split("-")[1:])
            if problemName not in problemNames:
                
                genTarget(ctx)
                problemNames.add(problemName)
                problemIDs.append(ctx.problemName)
            
            logger.info("completed processing " + path)

        except Exception as e:
            if e in tolerableExceptions:
                logger.warning(e)
            else:
                logger.error(e, exc_info=True)

            
        

       



    
    # generate course metdata data 
    problemIDs = sorted(problemIDs, key=lambda x: int(x.split("-")[0]))
    
    infoAssessment = {
        "uuid": "cef0cbf3-6458-4f13-a418-ee4d7e7505dd",
        "type": "Exam",
        "title": "Chem 101 quiz1",
        "set": "Quiz",
        "number": "1",
        "allowAccess": [
            {
                "startDate": "2015-01-19T16:00:00",
                "endDate": "2025-01-19T18:00:00",
                "timeLimitMin": 1,
                "credit": 10
            }
        ],
        "zones": [
            {
                "title": "option response test",
                "comment": "option response dev test",
                "questions": [{"id": id, "autoPoints": [10, 10]} for id in problemIDs]
            }
        ],
        "comment": "You can add comments to JSON files using this property."
    }
    with open("out/courseInstances/sample_questions/infoAssessment.json", "w") as f:
        f.write(json.dumps(infoAssessment, indent=4))

