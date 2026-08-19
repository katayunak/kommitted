"""Constants that belong to no single package.

Everything else moved next to the code that uses it:

    git/constants.py            message shape, settings keys, user messages
    brains/constants.py         LLM settings, shared confidence floor
    brains/rules/constants.py   path markers, branch prefixes, reasons
"""

# 2 is reserved: argparse uses it for usage errors.
EXIT_OK = 0
EXIT_ERROR = 1
