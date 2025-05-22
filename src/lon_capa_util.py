

#------------------------ lon-capa built-in utilities ------------------------

#todo: need to revist the behavior of theses lon-capa built-in functions
def lon_capa_func_random(lb: int|float, ub: int|float, step: int|float) -> int|float:
    from random import randint
    from decimal import Decimal
    lowerBound = min([lb, ub])
    upperBound = max([lb, ub])
    
    ri = randint(0, int((upperBound-lowerBound) // step))
    res = Decimal(str(lowerBound)) + Decimal(str(ri)) * Decimal(str(step))
    if type(lowerBound) == int and type(upperBound) == int and type(step) == int:
        return int(res)
    return float(res)

def lon_capa_func_format(num: float, pattern: str) -> float:
    import re
    if re.match("\\d+[sS]", pattern): 
        numSig = int(pattern[:-1])
        return float(("{0:." + str(numSig) +"g}").format(num))
    
    if re.match("\\d+[eEfFg]", pattern):
        p = "{0:." + pattern + "}"
        return float(p.format(num))
    
    raise Exception("unsupported answer format " + pattern)


def lon_capa_func_roundto(num: str|float, decimalNum: str|int) -> float:
    num = float(num)
    decimalNum = int(decimalNum)
    return float(("{0:." + str(decimalNum) +"f}").format(num))



def lon_capa_func_prettyprint(num: str|float, pattern, optionalTarget=None) ->str:
    import re
    if re.match("\\d+[sS]", pattern): 
        numSig = int(pattern[:-1])
        return ("{0:." + str(numSig) +"g}").format(num)
    
    if re.match("\\d+[eE]", pattern):
        p = "{0:." + pattern + "}"
        formatted = p.format(num)
        sep = "e" if "e" in pattern else "E"
        mantissa, exp = formatted.split(sep)
        return "{}\u00D710^{}".format(mantissa, str(int(exp)))
    
    if re.match("\\d+[fF]", pattern):
        p = "{0:." + pattern + "}"
        return p.format(num)
    
    raise Exception("unsupported pretty print format " + pattern)



def lon_capa_func_sqrt(num):
    import math 
    return math.sqrt(num)


def lon_capa_func_log(num):
    import math 
    return math.log(num)

def lon_capa_func_log10(num):
    import math 
    return math.log10(num)


def lon_capa_func_abs(num):
    return abs(num)

def lon_capa_func_pow(num, exp):
    return num ** exp


def lon_capa_func_exp(num):
    import math 
    return math.exp(num)
