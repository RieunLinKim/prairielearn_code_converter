from perl_translator.lexer import *
from util.logger import logger

def pythonize(perlScript: str) -> str:
    tokens = lex(perlScript)
    out = []
    locals = set()
    for i in range(len(tokens)):
        tokenType, value = tokens[i]
        if tokenType == ID:
            if value.startswith("$"):
                if i+1<len(tokens) and tokens[i+1][0] == L_SB:  # an array indexing op
                    id = "vector_"+value[1:]
                else:
                    id = "scalar_"+value[1:]
            elif value.startswith("@"):
                id = "vector_"+value[1:]
            elif value.startswith("&"):
                id = "lon_capa_func_"+value[1:]
            locals.add(id)
            out.append(id)
        
        elif tokenType == BAREWORD: # treat them as string for now
            out.append('"{}"'.format(value))
        
        elif tokenType == STRING:
            # perl is weak-typed, strip float/int from string type
            # in case later reference in computation
            if (
                ((m := DEF[FLOAT_FIXED].match(value)) != None and len(m.group(0)) == len(value)) or 
                ((m := DEF[FLOAT_SCIENTIFIC].match(value)) != None and len(m.group(0)) == len(value)) or 
                ((m := DEF[INT_DECIMAL].match(value)) != None and len(m.group(0)) == len(value))
            ):
                out.append(value)
            elif value.strip().startswith("<img"):
                plFigureElem = evaluateImageElem(value)
                out.append('"""' + plFigureElem +'"""')    # reduce raw img element to pl-figure
            else:
                out.append(templateString(value, locals))
        

        elif tokenType == SEMICOL:
            out.append("\n")

        #todo: add implicit str converstion for operands
        elif tokenType == OP_CONCAT:    
            out.append("+")


        elif tokenType == COMMENT_BLOCK:
            lines = value.split("=")[1].split("\n")
            comment = "\n".join(["#"+line for line in lines]) + "\n"
            out.append(comment)

        else:
            out.append(value)

    return "".join(out)

def evaluateImageElem(text: str) -> str:
    srcRegex = 'src=\\".*(res/[^")]+\\")'
    searched = re.search(srcRegex, text)
    if searched is None:
        logger.warning("Failed to match image element pattern: %s" % text)
        return text
    srcLink = searched.group(1)[:-1]
    fileName = srcLink.split("/")[-1]
    return '<pl-figure file-name="{}" directory="clientFilesQuestion"></pl-figure>'.format(fileName)



def templateString(text: str, locals: set) -> str:
    identifierRegex = "\\$[a-zA-Z_][a-zA-Z0-9_]*"
    arrayIndexingRegex = "^{}\\[{}\\]".format(identifierRegex, identifierRegex)
    result = []
    i = 0
    templateValueExprs = []
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
                if arrayName not in locals:
                    result.append(matched)
                    i += len(matched)
                    continue
                
                if idxExpr.isdigit():
                    idxSym = str(int(idxExpr[1:-1])) 
                else:
                    idxSym = "scalar_" + idxExpr[1:-1]
                    if idxSym not in locals:
                        result.append(matched)
                        i += len(matched)
                        continue
                
                expr = "{}[{}]".format(arrayName, idxSym)
                templateValueExprs.append(expr)

                result.append("{}")
                i += len(matched)
            elif (matched := re.match(identifierRegex, text[i:])):
                matched = matched.group(0)
                varName = "scalar_" + matched[1:]
                if varName not in locals:
                    result.append(matched)
                    i += len(matched)
                    continue
                
                result.append("{}") 
                templateValueExprs.append(varName)
                i += len(matched)
            else:
                result.append(chr)
                i += 1
             
    string = '"""' + "".join(result) + '"""'
    if len(templateValueExprs) > 0:
        string += ".format(" + ", ".join(templateValueExprs) + ")"
    return string
