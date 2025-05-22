import json
from random import sample, shuffle
from typing import List, Tuple, Any
import copy
import re
from collections import defaultdict


# ------------------ prairielearn interfaces start ------------------
def generate(plData: dict) -> None:
    
    problemData = loadProblemData(plData)

    
    while True:
        variables = genVariables(problemData.get("script", []), problemData.get("embeddedExprs", {}))
        problemVariant = genVariant(problemData, variables, maxRetry=3)
        # retry problem variable generation if some does not fit specified constraints 
        # such as number of significant digits
        if problemVariant is not None:
            break

    plData["params"]["questions"] = problemVariant
    plData["params"]["generatedVars"] = variables


def parse(plData: dict) -> None:
    problemData = loadProblemData(plData)
    for questionId, question in problemData["questions"].items():
        
        if question.get("isNumericalResponse"):
            parseNumericalResponse(question,questionId,  plData)
        elif question.get("isStringResponse"):
            parseStringResponse(question, questionId, plData)
        elif question.get("isReactionResponse"):
            parseReactionResponse(question, questionId, plData)

# ------------------ prairielearn interfaces end ------------------
# compare if two reactions are the same
def CompareReaction(student_answer:str, right_answer:str):
    if student_answer.find("->") == -1 or right_answer.find("->") == -1:
        return False
    right_answer_reactants, right_answer_products = ParseReaction(right_answer)
    student_answer_reactants,student_answer_products = ParseReaction(student_answer)
    if right_answer_reactants == student_answer_reactants and right_answer_products == student_answer_products:
        return True
    else:
        return False

def ParseReaction(answer:str):
    answer = answer.replace(" ","")
    segment_index = answer.find("->")

    reactants = answer[:segment_index]
    products = answer[(segment_index+2):]

    reactants = reactants.split("+")
    products = products.split("+")

    reactants = sorted(reactants)
    products = sorted(products)

    return reactants,products

def parseReactionResponse(question: dict, questionId, plData: dict) -> None:
    variables = plData["params"]["generatedVars"].get(question.get("scope"), {})
    answerValue = str(evaluateEmbeddedExprs(question["answerValue"], variables))

    if (value := plData["submitted_answers"].get(questionId)) is None:
        plData["format_errors"][questionId] = "Empty input."
        return
    isCorrect = False
    if question.get("isReactionResponse"):
        isCorrect = CompareReaction(answerValue,value)

    plData["submitted_answers"][questionId] = answerValue if isCorrect else value

# check correctness of string input according to specified match type
def parseStringResponse(question: dict, questionId, plData: dict) -> None:
    variables = plData["params"]["generatedVars"].get(question.get("scope"), {})
    answerValue = str(evaluateEmbeddedExprs(question["answerValue"], variables))

    if (value := plData["submitted_answers"].get(questionId)) is None:
        plData["format_errors"][questionId] = "Empty input."
        return
    isCorrect = False
    matchType = question["matchType"]

    if matchType == "cs": # case-sensitive exact match
        isCorrect = value == answerValue
    elif matchType == "ci": # case-insensitive exact match
        isCorrect = value.lower() == answerValue.lower()
    elif matchType == "mc": #multiple choice, ordering does not matter
        isCorrect = sorted(value) == sorted(answerValue)
    elif matchType == "re":
        isCorrect = re.match(answerValue, value) != None
    else:
        raise Exception("Unknown string match type")
    
    plData["submitted_answers"][questionId] = answerValue if isCorrect else value



    
def parseNumericalResponse(question: dict, questionId,  plData: dict) -> None:
    sigRange = question.get("sigRange")

    if (value := plData["submitted_answers"].get(questionId)) is None:
        plData["format_errors"][questionId] = "Empty input."
        return
    # verify answer has a valid number of significant digits
    if questionId not in plData["format_errors"] and (not checkSigCount(str(value), sigRange)):
        plData["format_errors"][questionId] = "Invalid number of significant figures"



def genVariant(problemData: dict, variables: dict, maxRetry: int = 10) -> dict:

    if maxRetry <= 0:
        return None
    
    questions = problemData.get("questions", {})

    variants = dict()

    for questionId, question in questions.items():
        inScopeVars = variables.get(question["scope"])
        if inScopeVars is None:
            inScopeVars = variables.get("scope_default", {})
        
        if question.get("isOptionResponse"):
            variant = genOptionResponseVariant(question, questionId, inScopeVars)
        elif question.get("isStringResponse"):
            variant = genStringResponseVariant(question, inScopeVars)

        elif question.get("isNumericalResponse"):
            variant = genNumericalResponseVariant(question, inScopeVars)
        
        elif question.get("isRankResponse"):
            variant = genRankResponseVariant(question, inScopeVars)
        elif question.get("isRadioButtonResponse"):
            variant = genRadioButtonResponseVariant(question, inScopeVars)
        elif question.get("isReactionResponse"):
            variant = genReactionResponseVariant(question, inScopeVars)
        else:
            raise Exception("Unsupported question type")

        # generated variable is illegal, retry
        if variant is None:
            return genVariant(problemData, variables, maxRetry-1)
        

    
        variants[questionId] = variant

    return variants

def genStringResponseVariant(question: dict, variables: dict) -> dict:
    res = copy.deepcopy(question)
    res["answerValue"] = evaluateEmbeddedExprs(res["answerValue"], variables)
    return res

def genReactionResponseVariant(question: dict, variables: dict) -> dict:
    res = copy.deepcopy(question)
    res["answerValue"] = evaluateEmbeddedExprs(res["answerValue"], variables)
    return res

def genRadioButtonResponseVariant(question: dict, variables: dict = {}) -> dict:
    maxDisplayNum = question["maxDisplayed"]
    randomizeDisplayOrder = question.get("randomizeDisplayOrder", False)
    candidates = question["foils"]
    
    correctChoices = [] #indices of correct choices
    incorrectChoices = [] #indices of incorrect choices
    renderedChoices = []
    seenChoicePrompt = set()
    idx = 0
    defaultChoiceId = 1

    for foil in candidates:
        value = str(evaluateEmbeddedExprs(foil["answerValue"], variables)).lower()
        if value not in ["true", "false"]:
            raise Exception("Invalid radio button response foil answer value")
        foilPrompt = evaluateEmbeddedExprs(foil["foilPrompt"], variables)
        

        #avoid duplicate choice which causes prairielearn error
        if foilPrompt in seenChoicePrompt:  
            continue
        #provide a default choice prompt, otherwise PrairieLearn will complain
        if foilPrompt is None or len(foilPrompt) == 0:
            foilPrompt = "Choice " + str(defaultChoiceId)
            defaultChoiceId += 1
        seenChoicePrompt.add(foilPrompt)
        rendered = {"answerValue": value, "foilPrompt": foilPrompt}
        renderedChoices.append(rendered)
        
        if value == "true":
            correctChoices.append(idx)
        else:
            incorrectChoices.append(idx)
        idx += 1

    # radio button response variant has no correct choice, redo variant generation
    if len(correctChoices) == 0:

        return None
    
    selectedChoices = [] #indices of selected choices
    # radio button response only shows one correct choice
    selectedChoices += sample(correctChoices, 1)
    incorrectChoicesNum = min(maxDisplayNum-1,len(incorrectChoices)) if maxDisplayNum-1>0 else len(incorrectChoices)
    selectedChoices += sample(incorrectChoices, incorrectChoicesNum)
    
    if randomizeDisplayOrder:
        shuffle(selectedChoices)
    else:
        selectedChoices = sorted(selectedChoices) # respect original ordering

    res = [renderedChoices[idx] for idx in selectedChoices]
    
    return {
        "foils": res
    }



def genOptionResponseVariant(question: dict, questionId: str, variables) -> dict:
    def filter(foils: list, options: list) -> list:
        res = []
        for foil in foils:
            ans = str(evaluateEmbeddedExprs(foil["answerValue"], variables))
            if ans in options:
                res.append(foil)
        return res 
    
    randomizeDisplayOrder = question.get("randomizeDisplayOrder", False)
    maxDisplayNum = question["maxDisplayed"]
    selected = []

    options = question["options"]

    # filter out questions with invalid options
    for q in question["foils"]:
        if q.get("isConceptGroup", False):
            selected.append(sample(filter(q["candidates"], options), 1)[0])
        else:
            selected += filter([q], options)
    
    sampleNum =  min(len(selected), maxDisplayNum) if maxDisplayNum > 0 else len(selected)

    if randomizeDisplayOrder:
        foils = sample(selected, sampleNum)
        shuffle(foils)
    else:
        foils = orderPreservingSample(selected, sampleNum)

    rendered = []
    foilId = 1
    for foil in foils:
        answer = str(evaluateEmbeddedExprs(foil["answerValue"], variables))
        renderedOps = [{"option": op, "answerValue": op == answer} for op in options]
        
        rendered.append({
            "answerId": "{}-{}".format(questionId, str(foilId)),
            "foilPrompt": evaluateEmbeddedExprs(foil["foilPrompt"], variables),
            "options": renderedOps
        })

        foilId += 1
    
    return {
        "foils": rendered
    }


def genNumericalResponseVariant(question: dict, variables: dict = {}) -> dict:

    answer = renderNumericAnswer(question, variables)
    if answer is None:
        return None

    tolType, tolerance = getTolerance(question, variables)
    #prairielearn marks answer as correct if it falls in either 
    #relative tolerance or absolute tolerance range
    #both have default values if not specified, hence we need to limit
    #the other one to be 0
    if tolType == "rtol":
        rtol = tolerance
        atol = 0
    else:
        rtol = 0
        atol = tolerance
        
    return {
        "atol": atol,
        "rtol": rtol,
        "answerValue": answer
    }


def genRankResponseVariant(question: dict, variables) -> dict:
    randomizeDisplayOrder = question.get("randomizeDisplayOrder", False)
    maxDisplayNum = question["maxDisplayed"]
    candidates = question["foils"]

    sampleNum =  min(len(candidates), maxDisplayNum) if maxDisplayNum > 0 else len(candidates)
    

    if randomizeDisplayOrder:
        foils = sample(candidates, sampleNum)
        shuffle(foils)
    else:
        foils = orderPreservingSample(candidates, sampleNum)

    output = []
    for foil in foils:
        output.append({
            "foilName": foil["foilName"],
            "foilPrompt": str(evaluateEmbeddedExprs(foil["foilPrompt"], variables)),
            "rank": str(evaluateEmbeddedExprs(str(foil["rank"]), variables)),
        })


    return {
        "foils": output
    }

    

# returns None if generated answer does not conform to constraints
def renderNumericAnswer(question: dict, variables: dict) -> float|None:

    answerExpr: str = question.get("answerValue")
    if answerExpr is None:
        raise Exception("No answer expression found for question")
    
    answer = float(evaluateEmbeddedExprs(answerExpr, variables))

    #format answer
    answerFormat = question.get("answerFormat")
    if answerFormat != None:
        answerRpr = formatAns(answer, answerFormat)
    else:
        answerRpr = str(answer)
    
    # check for number of significant digits
    sigRange = question.get("sigRange", [])
    if not checkSigCount(answerRpr, sigRange):
        return None

    return float(answerRpr)

    
# check if a number has a valid number of significant numbers
def checkSigCount(num: str, sigRange: List[int]|None) -> bool:
    if sigRange is None:
        return True
    sigCount = countNumSig(num)

    if ((len(sigRange) > 0 and sigCount < sigRange[0]) or
         (len(sigRange) > 1 and sigCount > sigRange[1])):
        return False
    
    return True

def formatAns(num: float, pattern: str) -> str:

    if re.match("\\d+[sS]", pattern): 
        numSig = int(pattern[:-1])
        return ("{0:." + str(numSig) +"g}").format(num)
    
    if re.match("\\d+[eEfFg]", pattern):
        p = "{0:." + pattern + "}"
        return p.format(num)
    
    raise Exception("unsupported answer format " + pattern)

    
def getTolerance(problemData: dict, variables: dict) -> Tuple[str, float]:
    if (tolRpr := problemData.get("tolerance")) is not None:
        if tolRpr.endswith("%"):
            tol = float(tolRpr[:-1])/100
            tolType = "rtol"
            
        else:
            tol = float(evaluateEmbeddedExprs(tolRpr, variables)) 
            tolType = "atol"
    else:
        tolType = "atol"
        tol = 1e-8  #1e-8 is the prairielearn default tolerance

    return (tolType, tol) 

    
    
# execute python script and return a mapping of local variables for each scope
def genVariables(_scope2Script: list[tuple[str, str]], _scope2Exprs: dict[str, dict]) -> dict:
    
    _res = defaultdict(dict)
    for _scope, _script in _scope2Script:
        exec(_script)
        for _varName, _expr in _scope2Exprs.get(_scope, {}).items():
            _res[_scope][_varName] = eval(_expr)
    return _res


def loadProblemData(plData: dict) -> dict:
    if not plData["params"].get("problemDataLoaded", False):
        problemDataPath = plData["options"]["question_path"] + "/data.json"
        with open(problemDataPath, "r") as f:
            plData["params"]["problemDataStr"] = f.read()
        plData["params"]["problemDataLoaded"] = True

    problemData = json.loads(plData["params"]["problemDataStr"])
    return problemData




# counts #significant number for int and float representations
# returns -1 for invalid strings
def countNumSig(num: str) -> int:

    if not re.match("[+-]?\\d+|\\d*\\.\\d*", str(num)):
        return -1
    
    if not "." in num:
        return len(num.strip("0+-"))

    count = 0

    for chr in num:
        if chr in "eE":
            break
        if chr in "+-.":
            continue
        elif chr == "0":
            count += 1 if count > 0 else 0
        else:
            count += 1
    return count

# replace placeholders with actual values generated by the script
def evaluateEmbeddedExprs(text: str, variables: dict) -> str:
    def replace(matched):
        valueName = matched.group(0).strip("}{").split(".")[-1]

        return str(variables.get(valueName, matched.group(0)))

    res = re.sub("{{value-\d+}}", replace, text)
    
    return res



def orderPreservingSample(candidates: List[Any], sampleNum: int) -> List[Any]:
    return [
        candidates[i] for i in sorted(sample(list(range(len(candidates))), sampleNum))
    ]
