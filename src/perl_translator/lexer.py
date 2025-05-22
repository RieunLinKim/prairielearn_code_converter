from typing import List, Tuple, Any
import xml.etree.ElementTree as ET
import re


# token types
BLANK = 1
ID = 2
INT_DECIMAL = 3
FLOAT_FIXED = 4
FLOAT_SCIENTIFIC = 5
STRING = 6

OP_EXP = 11
OP_ADD = 12 
OP_MINUS = 13 
OP_MULT = 14 
OP_DIV = 15 
OP_MOD = 16

NEQ = 17 
EQ = 18 
LT = 19 
GT = 20 
LE = 21 
GE = 22

AND = 23 
OR = 24 
NOT = 25 


LP = 26 
RP = 27 
L_SB = 28 
R_SB = 29 
L_CB = 30 
R_CB = 31 

ARROW = 32 

COMMA = 35 
SEMICOL = 36 
DOUBLE_DOT = 37   # range op (1..100) (a..z) 
DOT = 38          # string concat op


FOR = 39 
KEYS = 40 


IF = 41 
ELSE = 42 
ELIF = 43

OP_ASSIGN = 44

BAREWORD = 45

OP_CONCAT = 46

COMMENT_SINGLE_LINE = 47

COMMENT_BLOCK = 48


symbolName = {
    BLANK : "BLANK",
    ID : "ID",
    INT_DECIMAL : "INT_DECIMAL",
    FLOAT_FIXED : "FLOAT_FIXED",
    FLOAT_SCIENTIFIC : "FLOAT_SCIENTIFIC",
    STRING : "STRING",

    OP_EXP : "OP_EXP",
    OP_ADD : "OP_ADD",
    OP_MINUS : "OP_MINUS",
    OP_MULT : "OP_MULT", 
    OP_DIV : "OP_DIV", 
    OP_MOD : "OP_MOD", 
    OP_ASSIGN : "OP_ASSIGN",
    OP_CONCAT: "OP_CONCAT",

    NEQ : "NEQ", 
    EQ : "EQ", 
    LT : "LT", 
    GT : "GT", 
    LE : "LE", 
    GE : "GE",

    AND : "AND", 
    OR : "OR", 
    NOT : "NOT", 


    LP : "LP", 
    RP : "RP", 
    L_SB : "L_SB", 
    R_SB : "R_SB", 
    L_CB : "L_CB", 
    R_CB : "R_CB", 

    ARROW : "ARROW", 

    COMMA : "COMMA", 
    SEMICOL : "SEMICOL", 
    DOUBLE_DOT : "DOUBLE_DOT",   # range op (1..100) (a..z) 
    DOT : "DOT",          # string concat op


    FOR : "FOR", 
    KEYS : "KEYS", 


    IF : "IF", 
    ELSE : "ELSE", 
    ELIF : "ELIF",

    BAREWORD: "BAREWORD",
    COMMENT_SINGLE_LINE: "COMMENT_SINGLE_LINE",
    COMMENT_BLOCK: "COMMENT_BLOCK"

}



DEF = {
    BLANK : "[\\s\\n\\r\\t]+",

    ID : "[$@&][a-zA-Z_][a-zA-Z0-9_]*",

    INT_DECIMAL : "^[+-]?[0-9][0-9_]*",
    FLOAT_FIXED : "^[+-]?[0-9]*\\.[0-9]+|^[+-]?[0-9]+\\.[0-9]*",
    FLOAT_SCIENTIFIC : "^[+-]?[0-9]*\\.[0-9]+[Ee][+-]?[0-9]+",



    OP_EXP : "\\*\\*",
    OP_ADD : "\\+",
    OP_MINUS : "-",
    OP_MULT : "\\*",
    OP_DIV : "/",
    OP_MOD : "%",
    OP_ASSIGN : "=",
    OP_CONCAT : "\\.",

    NEQ : "!=",
    EQ : "==",
    LT : "<",
    GT : ">",
    LE : "<=",
    GE : ">=",

    AND : "&&",
    OR : "\\|\\|",
    NOT : "\\!",


    LP : "\\(",
    RP : "\\)",
    L_SB : "\\[",
    R_SB : "\\]",
    # L_CB : "{",
    # R_CB : "}",

    # ARROW : "=>",

    COMMA : ",",
    SEMICOL : ";",
    DOUBLE_DOT : "\\.\\.",  # range op (1..100) (a..z) 
    DOT : "\\.",         # string concat op

    BAREWORD : "[a-zA-Z]+",
    COMMENT_SINGLE_LINE: "\\#[^\\n]*\\n",
    COMMENT_BLOCK: "=.*=cut",


    # FOR : "for",
    # KEYS : "keys",


    # IF : "if",
    # ELSE : "else",
    # ELIF : "elsif"
}

for k, v in DEF.items():
    DEF[k] = re.compile(v, flags=re.MULTILINE|re.DOTALL)


def parseString(instream: str):
    
    delimiter = instream[0]
    if not delimiter in ['"', "'"]:
        raise Exception("Invalid string delimiter")
    
    i = 1
    while i < len(instream):
        chr = instream[i]
        if chr == "\\":
            i += 2 
        elif chr == delimiter:
            # deal with trailing double quote to avoid messing up the triple quote we apply 
            string = instream[1:i]
            if string.endswith('"'):
                string = string[:-1] + '\\"'
            return (string, i+1)
        else:
            i += 1
    raise Exception ("Unclosed string")



def lex(perlScript: str) -> List[Tuple[int, str]]:
    tokens = []
    cursor = 0

    while cursor < len(perlScript):

        #parse string separately
        if perlScript[cursor] in ["'", '"']:
            string, length = parseString(perlScript[cursor:])
            cursor += length
            tokens.append((STRING, string))
            continue



        lexemeType = None
        value = None
        for type, regex in DEF.items():
            
            if (matched := regex.match(perlScript[cursor:])) == None:
                continue
            v = matched.group(0)
            if len(v) == 0:
                raise Exception(symbolName[type], "matches empty string")

            #try match the longest string
            if value is None or len(v) > len(value):
                value = v 
                lexemeType = type

               
        if lexemeType is None or value is None:
            raise Exception("Lexer failed. No rules matched at: " + perlScript[cursor:])
        
        cursor += len(value)

        
        if lexemeType != BLANK:
            tokens.append((lexemeType, value))
            
        
    return tokens

        



