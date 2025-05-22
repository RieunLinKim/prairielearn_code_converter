import xml.etree.ElementTree as ET
from typing import (List, Any)
from pathlib import Path
from util.execution_manager import ExecutionManager
import json
import shutil
import os
import uuid
import pystache
import re
from html import escape, unescape
from util.logger import logger

from . import exceptions




#todo: initialize output dir
_base_output_dir = "out/questions"



# context for writing translation result to file
# one for each problem
class Context():

    def __init__(self, srcQuestionDir: str) -> None:
        problemFileFound = False
        for file in os.listdir(srcQuestionDir):
            filePath = srcQuestionDir + "/" + str(file)
            if os.path.isfile(filePath) and filePath.endswith(".problem"):
                self.xmlRoot = self._parseXml(filePath)
                if self.xmlRoot.find("problem") is None:
                    raise exceptions.INVALID_PROBLEM_DEFINITION
                self.problemName = str(srcQuestionDir).split("/")[1] + "-" + str(file).split(".")[0]
                problemFileFound = True
                break 
        if not problemFileFound:
            raise exceptions.PROBLEM_FILE_NOT_FOUND
        
        self._problemData = dict()
        self._problemData["questions"] = []
        self._executionManager = ExecutionManager()

        self._srcQuestionDir = srcQuestionDir + "/"
        self._dstQuestionDir: str = _base_output_dir + "/" + self.problemName + "/"
        self._exprCounter = 1
        self._ansCounter = 1
        
        


    
    def getAnswerId(self) -> str:
        id = "ans-"+str(self._ansCounter)
        self._ansCounter += 1
        return id

    

    def openNewQuestion(self) -> None:
        self._problemData["questions"].append(dict())

    # escape characters and replace xml special chars
    def _cleanXml(self, xml: str) -> str:

        # escape all dangling '&'s
        escaped = []
        for i in range(len(xml)):
            if xml[i] == "&" and xml[i:i+5] != "&amp;":
                escaped.append("&amp;")
            else:
                escaped.append(xml[i])
        xml = "".join(escaped)

        #escape <, > within script
        start = False
        escaped = []
        i = 0
        while i<len(xml):
            if i+28 < len(xml) and xml[i:i+28] == '<script type="loncapa/perl">':
                start = True
                escaped.append('<script type="loncapa/perl">')
                i += 28
            elif i+9 < len(xml) and xml[i:i+9] == "</script>":
                start = False
                escaped.append("</script>")
                i += 9
            elif start:
                if xml[i] == "<":
                    escaped.append("&lt;")
                elif xml[i] == ">":
                    escaped.append("&gt;")
                else:
                    escaped.append(xml[i])
                i += 1
            else:
                escaped.append(xml[i])
                i += 1
        xml = "".join(escaped)

        xml = re.sub("<\\s", "&lt; ", xml)
        xml = re.sub("\\s>", " &gt;", xml)
        return xml
    

    def _parseXml(self, path) -> ET.Element:
        with open(path, "r", encoding="utf-8") as f:
            xml = f.read()

        if "<html>" in xml:
            raise exceptions.HTML_NOT_SUPPORTED
        if "<customresponse" in xml:
            raise exceptions.CUSTOM_RESPONSE_NOT_SUPPORTED
        xml = "<root>" + xml + "</root>"
        xml = self._cleanXml(xml)
        return ET.fromstring(xml)
    

    def genTargetResource(self) -> None:
        dstPath = Path(self._dstQuestionDir)
        if not dstPath.exists():
            dstPath.mkdir(parents=True)
        try:
            self._executionManager.verifyExecution()
        except Exception as e:
            logger.error("Error verifying execution: %s" % e)

            
        self._genProblemMetadata()
        self._genProblemHtml()
        self._genServerScript()
        self._dumpProblemData()



        


    # write data used for rendering the question to file 
    def _dumpProblemData(self) -> None:
        data = dict()
        data["script"] = self._executionManager.dumpScripts()
        data["questions"] = dict()
        data["embeddedExprs"] = self._executionManager.dumpReferences()
        for question in self._problemData["questions"]:
            
            if not "answerId" in question:
                continue 
            question.pop("prompt")
            if "hint" in question:
                question.pop("hint")
            ansId = question.pop("answerId")
            data["questions"][ansId] = question
        
            
        data = json.dumps(data, indent=4)
        with open(self._dstQuestionDir + "data.json", "w") as f:
            f.write(data)



    def _genProblemHtml(self) -> None:
        htmlPath = "src/templates/question.html"
        data = self._problemData
        with open(htmlPath, "r", encoding="utf-8") as f:
            template = f.read()
            
        rendered = pystache.render(template, data)
        rendered = rendered.replace("\\{", "{")
        rendered = rendered.replace("\\}", "}")
        rendered = re.sub("\\&#?\\w+\\;", lambda x: escape(unescape(x.group(0))), rendered)
        try:
            elem = ET.fromstring(rendered)
        except Exception as e:
            logger.warning(f"failed to parse \n {rendered} \n with error {e}")
            return
        ET.indent(elem)
        with open(self._dstQuestionDir + "question.html", "w", encoding="utf-8") as f:
            f.write(ET.tostring(elem, encoding="unicode", short_empty_elements=False))


    def _genServerScript(self) -> None:
        scriptPath = "src/templates/server.py"
        lonCapaUtilPath = "src/lon_capa_util.py"
        with open(scriptPath, "r") as f:
            script = f.read()
        with open(lonCapaUtilPath, "r") as f:
            lon_capa_util = f.read()
        code = script + "\n" + lon_capa_util
        with open(self._dstQuestionDir + "server.py", "w") as f:
            f.write(code)


    def _genProblemMetadata(self) -> None:
        metadata = {
            "uuid": str(uuid.uuid4()),
            "title": self.problemName,
            "topic": "to-be-assigned",
            # "tags": ["secret", "Fa18"],
            "type": "v3",
            "comment": "You can add comments to JSON files using this property."
        }

        with open(self._dstQuestionDir + "info.json", "w") as f:
            f.write(json.dumps(metadata, indent=4))

    
    def setPrompt(self, prompt: str) -> None:
        prompt = prompt.strip("\n ")
        if len(self._problemData["questions"]) == 0 or self._problemData["questions"][-1].get("prompt") is not None:
            self.openNewQuestion()
        self._problemData["questions"][-1]["prompt"] = prompt


    def setHint(self, precedingText: str, hintPrompt: str, hintFileLinks: List[str] = []) -> None:
        # for some reason, some lon-capa questions had empty hint
        if len(hintPrompt.strip())==0 and  len(hintFileLinks) == 0:
            return
        if len(self._problemData["questions"]) == 0 or self._problemData["questions"][-1].get("hint") is not None:
            self.openNewQuestion()
        data = self._problemData["questions"][-1]
        data["hint"] = dict()
        data["hint"]["precedingText"] = precedingText
        data["hint"]["prompt"] = hintPrompt
        data["hint"]["files"] = []
        for link in hintFileLinks:
            elem = dict()
            name = link.split("/")[-1]
            filePath = Path(self._srcQuestionDir + "/res/" + name)
            if not filePath.is_file():
                logger.warning("Unable to locate file %s while parsing hint" % link)
                continue
            elem["name"] = name
            if len(name.split(".")) > 1:
                suffix = name.split(".")[-1]
                if suffix in ["html", "htm"]:
                    elem["isHTML"] = True 
                elif suffix in ["jpg", "jpeg", "png", "gif", "svg", "tif", "tiff"]:
                    elem["isImage"] = True
                else:
                    elem["isUnknownType"] = True
            else:
                elem["isUnknownType"] = True
            
            data["hint"]["files"].append(elem)
 

    def setProblemField(self, fieldName: str, value: Any) -> None:
        self._problemData["questions"][-1][fieldName] = value

    def setMaxDisplayNum(self, num: int) -> None:
        self.setProblemField("maxDisplayed", num)

    def setProblem(self, type: str, problemDef: dict, scope: str) -> None:
        if len(self._problemData["questions"]) == 0 or self._problemData["questions"][-1].get("type") is not None:
            self.openNewQuestion()
        curQuestion = self._problemData["questions"][-1]

        if type == "stringresponse":
            curQuestion["isStringResponse"] = True
        elif type == "radiobuttonresponse":
            curQuestion["isRadioButtonResponse"] = True
        elif type == "optionresponse":
            curQuestion["isOptionResponse"] = True
        elif type == "rankresponse":
            curQuestion["isRankResponse"] = True
        elif type == "numericalresponse":
            curQuestion["isNumericalResponse"] = True
        elif type == "reactionresponse":
            curQuestion["isReactionResponse"] = True
        else:
            raise Exception("Unsupported problem type ", type)
        curQuestion["scope"] = scope
        for k, v in problemDef.items():
            curQuestion[k] = v


    def setScript(self, scope: str, script: str) -> None:
        self._executionManager.setScript(scope, script)

    def addReference(self, scope: str, expr: str) -> None:
        return self._executionManager.addReference(scope, expr)

    def getVisibleVariablesNames(self, scope: str) -> set[str]:
        return self._executionManager.getLocalVarNames(scope)

    #copy a file under src question dir to dst question file dir
    def moveStaticResources(self) -> None:
        srcPath = self._srcQuestionDir + "res"
        if not Path(srcPath).exists():
            return
        dstPath = Path(self._dstQuestionDir + "/clientFilesQuestion")
        if not dstPath.exists():
            dstPath.mkdir(parents=True)
        srcPath = self._srcQuestionDir + "/res"
        for file in os.listdir(srcPath):
            try:
                shutil.copy(srcPath + "/" + file, str(dstPath))
            except Exception as e:
                logger.error("Error moving static files: %s" % str(e))



        
        
