import copy
from util.logger import logger
import sys

# manages lon-capa script dynamic execution
# and embedded expression scope bindings
class ExecutionManager():
    
    SCOPE_DEFAULT = "__SCOPE_DEFAULT__"

    def __init__(self) -> None:
        self._scope2script: list[tuple[str, str]] = list()
        self._scope2reference: dict[str, dict[str, str]] = dict()
        self._scope2varNames: dict[str, list[str]] = dict()  #scope -> visible local vars
        self._exprCounter: int = 0
    

    def setScript(self, scope: str, script: str) -> None:
        for i in range(len(self._scope2script)):
            if scope == self._scope2script[i][0]:
                self._scope2script[i] = (scope, script)
                return
        self._scope2script.append((scope, script))


    # returns references name
    def addReference(self, scope: str, expr: str) -> str:
        if not scope in self._scope2reference:
            self._scope2reference[scope] = dict()
        
        for name, expression in self._scope2reference.items():
            if expression == expr:
                return name 
            
        newName =  "value-" + str(self._exprCounter)
        self._exprCounter += 1
        self._scope2reference[scope][newName] = expr
        return newName
    
    # execute a python script and obtain locals
    def _execute(self, __pyScript: str) -> dict:
        try:
            exec(__pyScript)
        except Exception as e:
            logger.error("Error running script: %s" % __pyScript)
            logger.error(e, exc_info=True)
            sys.exit(1)

        res = locals()
        return res
    

    def getLocalVarNames(self, scope: str) -> set[str]:
        if scope in self._scope2varNames:
            return self._scope2varNames[scope]
        
        scripts = []
        with open("src/lon_capa_util.py", "r", encoding="utf-8") as f:
            libScript = f.read()
            scripts.append(libScript)

        for scope1, script in self._scope2script:
            scripts.append(script)
            if scope1 == scope:
                break 

            
        script = "\n".join(scripts)

        try:
            variables = self._execute(script)
        except Exception as e:
            
            logger.error("Error generating local variable names for scope %s" % scope)
            logger.error("when running script: %s" % script)
            logger.error(e, exc_info=True)
            sys.exit(1)
            return set()
        
        varNames = set(variables.keys())
        self._scope2varNames[scope] = varNames
        return varNames

    

    # test run all scripts and embedded expression evaluation
    def verifyExecution(self) -> None:
        with open("src/lon_capa_util.py", "r", encoding="utf-8") as f:
            __libScript = f.read()        

        exec(__libScript)

        targetScopes = set(self._scope2reference.keys())

        for scope, script in self._scope2script:
            logger.info("Verifying execution for scope %s ..." % scope)
            if scope in targetScopes:
                targetScopes.remove(scope)
            if script is None or len(script.strip()) == 0:
                logger.info("No script found for scope %s ..." % scope)
                continue
            exec(script)
            for expr in self._scope2reference.get(scope, {}).values():
                assert(eval(expr) is not None)

        
        assert(len(targetScopes) == 0)


    def dumpScripts(self) -> dict:
        return copy.deepcopy(self._scope2script)
    

    def dumpReferences(self) -> dict:
        return copy.deepcopy(self._scope2reference)

        

