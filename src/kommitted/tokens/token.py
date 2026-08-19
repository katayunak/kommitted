import re
from dataclasses import dataclass
from enum import Enum

_TOKEN_RE = re.compile(
    r"""
      (?P<string> "(?:[^"\\]|\\.)*" | '(?:[^'\\]|\\.)*' | `[^`]*` ) # if the text looks like a string literal, mark it as string
    | (?P<number> \b\d+(?:\.\d+)?\b ) #if it looks like a number, mark it as number
    | (?P<name>  [A-Za-z_]\w* ) # if it looks like a variable name, mark it as name
    | (?P<op>     ===|!==|<<=|>>=|&&=|\|\|=|\*\*= # if it looks like an operator, mark it as op
                | ==|!=|<=|>=|&&|\|\||\+\+|--|->|=>|::|:=|\.\.\.
                | \+=|-=|\*=|/=|%=|\|=|&=|\^=|<<|>>|\?\?|\?\.
                | [-+*/%<>=!&|^~?] )
    | (?P<punct>  [(){}\[\],.;:] ) # if it looks like punctuation like ( or ,, mark it as punct
    """,
    re.VERBOSE,
)


class TokenType(str, Enum):
    STRING = "string"
    NUMBER = "number"
    NAME = "name"
    OP = "op"
    PUNCT = "punct"


@dataclass(frozen=True)
class Token:
    type: TokenType
    text: str


# in python words like and, or, not, in, is are operator-like
# the code wants them treated as TokenType.OP
_PYTHON_OPS_KEYWORDS = frozenset(
    {"and", "or", "not", "in", "is", "of", "instanceof", "typeof"}
)


def tokenize(line: str) -> list[Token]:
    tokens = []
    for match in _TOKEN_RE.finditer(line):
        # BUG THAT WAS HERE: `TokenType.name` (lowercase) is not the NAME
        # member. Every Enum has a built-in `.name` attribute, so Python
        # found that instead of raising, the check never matched, and
        # `and`/`or` stayed names. Enum members are case-sensitive.
        token_type = TokenType(match.lastgroup)
        if token_type is TokenType.NAME and match.group() in _PYTHON_OPS_KEYWORDS:
            token_type = TokenType.OP
        tokens.append(Token(token_type, match.group()))
    return tokens
