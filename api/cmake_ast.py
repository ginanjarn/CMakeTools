"""CMake AST"""

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import List, Union


logger = logging.getLogger("cmake_ast")
# logger.setLevel(logging.DEBUG)
sh = logging.StreamHandler()
logger.addHandler(sh)


class TokenKind(Enum):
    EOF = "eof"
    Identifier = "identifier"
    Text = "text"
    Newline = "newline"
    Space = "space"
    LParen = "lparen"
    RParen = "rparen"
    LBracket = "lbracket"
    RBracket = "rbracket"
    Quote = "quote"
    CommentMark = "commentmark"


class Token:
    __slots__ = ["pos", "kind", "text"]

    def __init__(self, pos: int, kind: TokenKind, text: str, /):
        self.pos = pos
        self.kind = kind
        self.text = text

    def __repr__(self):
        return f"Token(pos={self.pos}, kind={self.kind!r}, text={self.text!r})"

    def start(self):
        return self.pos

    def end(self):
        return self.pos + len(self.text)


class AST(ABC):
    """Abstract Syntax Tree"""

    @abstractmethod
    def start(self) -> int:
        """start offset"""

    @abstractmethod
    def end(self) -> int:
        """end offset"""

    @property
    @abstractmethod
    def text(self) -> str:
        """text"""


class Parser(ABC):
    """Abstract Parser"""

    @abstractmethod
    def __init__(self, source: str): ...

    @abstractmethod
    def parse(self) -> AST:
        """parse"""


class Leaf(AST):
    """Leaf of Syntax Tree

    Leaf is collection of Token
    """

    __slots__ = ["tokens"]
    kind = "leaf"

    def __init__(self, *token: Token):
        if not token:
            raise ValueError(f"require {Token} object")

        self.tokens = list(token)

    def __repr__(self):
        name = self.__class__.__name__
        return f"{name}(tokens={self.tokens})"

    def start(self):
        return self.tokens[0].start()

    def end(self):
        return self.tokens[-1].end()

    @property
    def text(self):
        return "".join([token.text for token in self.tokens])


class Node(AST):
    """Node of Syntax Tree

    Node is collection of Token, Leaf and Nodes
    """

    __slots__ = ["children"]
    kind = "node"

    def __init__(self, children: List[Union[Token, AST]]):
        self.children = children or []

    def __repr__(self):
        name = self.__class__.__name__
        return f"{name}(children={self.children})"

    def start(self):
        if not self.children:
            return -1
        return self.children[0].start()

    def end(self):
        if not self.children:
            return -1
        return self.children[-1].end()

    @property
    def text(self):
        def get_text(child: AST):
            if isinstance(child, list):
                node = child
                return "".join([child.text for child in node if child])
            return child.text

        return "".join([get_text(child) for child in self.children if child])


r"""
# CMake grammar

file ::= file_element*
file_element ::= command_invocation line_ending | (bracket_comment|space)* line_ending
line_ending ::= line_comment? newline
space ::= <match '[ \t]+'>
newline ::= <match '\n'>

command_invocation ::= space* identifier space* '(' arguments ')'
identifier ::= <match '[A-Za-z_][A-Za-z0-9_]*'>
arguments ::= argument? separated_arguments*
separated_arguments ::= separation+ argument? | separation* '(' arguments ')'
separation ::= space | line_ending
argument ::= bracket_argument | quoted_argument | unquoted_argument

bracket_argument ::= bracket_open bracket_content bracket_close
bracket_open ::= '[' '='* '['
bracket_content ::= <any text not containing a bracket_close with the same number of '=' as the bracket_open>
bracket_close ::= ']' '='* ']'

quoted_argument ::= '"' quoted_element* '"'
quoted_element ::= <any character except '\' or '"'> | escape_sequence | quoted_continuation
quoted_continuation ::= '\' newline

unquoted_argument ::= unquoted_element+ | unquoted_legacy
unquoted_element ::= <any character except whitespace or one of '()#"\'> | escape_sequence
unquoted_legacy ::= <see note in text>

escape_sequence ::= escape_identity | escape_encoded | escape_semicolon
escape_identity ::= '\' <match '[^A-Za-z0-9;]'>
escape_encoded ::= '\t' | '\r' | '\n'
escape_semicolon ::= '\;'
"""


class File(Node):
    """CMake file"""

    kind = "file"


class CommandInvocation(Node):
    """Command Invocation"""

    kind = "command_invocation"


class Arguments(list):
    """Arguments"""

    kind = "arguments"


class GroupedArguments(Arguments):
    """Grouped Arguments"""

    kind = "grouped_arguments"


class Argument(Leaf):
    """Base Argument"""

    kind = "argument"


class BracketArgument(Argument):
    """Argument wrapped by '[=*[' and ']=*]'"""

    kind = "bracket_argument"


class QuotedArgument(Argument):
    """Argument wrapped by '"' symbol"""

    kind = "quoted_argument"


class UnquotedArgument(Argument):
    """Argument without wrapping"""

    kind = "unquoted_argument"


class Comment(Leaf):
    """Comment"""

    kind = "comment"


class BracketComment(Comment):
    """Comment inside '#[=*[' and ']=*]'"""

    kind = "bracket_comment"


class LineComment(Comment):
    """Line comment"""

    kind = "line_comment"


class BracketTokens(list):
    """List of tokens wrapped by '[=*[' and ']=*]'"""


@dataclass
class TextPos:
    row: int
    col: int


def rowcol(text: str, offset: int) -> TextPos:
    """get row column form text at offset"""

    lines = text[:offset].splitlines(keepends=True)
    # use natural 1 based row index
    linenum = len(lines)
    colnum = len(lines[linenum - 1])
    return TextPos(linenum, colnum)


@dataclass
class MatchResult:
    pos: int
    text: str
    match: re.Match


class CMakeParser(Parser):
    def __init__(self, source: str):
        self.source = source
        self.offset = 0

    def eat_match(self, pattern: str) -> MatchResult:
        start = self.offset

        if match := re.match(pattern, self.source[start:]):
            end = start + match.span()[1]
            self.offset = end
            text = match.group(0)
            return MatchResult(start, text, match)

        return None

    def parse(self) -> File:
        self.offset = 0
        return self._parse()

    def _parse(self) -> File:
        temp = []
        while child := self.get_file_element():
            temp.append(child)
            if child.kind == TokenKind.EOF:
                break

        return File(temp)

    def get_file_element(self) -> Union[Token, Leaf, Node]:
        elements_opt = (
            self.get_command_invocation,
            self.get_comment,
            self.get_newline,
            self.get_space,
            self.get_eof,
        )
        for func in elements_opt:
            if child := func():
                return child

        pos = rowcol(self.source, self.offset)
        raise SyntaxError(f"syntax error at: {pos}")

    def get_eof(self) -> Token:
        if match := self.eat_match(r"$"):
            return Token(match.pos, TokenKind.EOF, match.text)
        return None

    def get_command_invocation(self) -> CommandInvocation:
        children = []
        ident = "[A-Za-z_][A-Za-z0-9_]*"

        if match := self.eat_match(ident):
            children.append(Token(match.pos, TokenKind.Identifier, match.text))
        else:
            return None

        if space := self.get_space():
            children.append(space)

        lparen = r"\("
        rparen = r"\)"

        if match := self.eat_match(lparen):
            children.append(Token(match.pos, TokenKind.LParen, match.text))
        else:
            pos = rowcol(self.source, self.offset)
            raise SyntaxError(f"requires '(' after identifier at {pos}")

        children.append(self.get_arguments())

        if match := self.eat_match(rparen):
            children.append(Token(match.pos, TokenKind.RParen, match.text))
        else:
            pos = rowcol(self.source, self.offset)
            raise SyntaxError(f"require closing ')' at {pos}")

        return CommandInvocation(children)

    def get_space(self) -> Token:
        space = r"[ \t]+"
        if match := self.eat_match(space):
            return Token(match.pos, TokenKind.Space, match.text)
        return None

    def get_newline(self) -> Token:
        newline = r"\n"
        if match := self.eat_match(newline):
            return Token(match.pos, TokenKind.Newline, match.text)
        return None

    def get_arguments(self) -> List[Argument]:
        arguments = []
        while argument := self.get_argument():
            arguments.append(argument)

        return arguments

    def get_argument(self) -> Argument:
        # argument children
        child_func = [
            self.get_grouped_arguments,
            self.get_bracket_argument,
            self.get_quoted_argument,
            self.get_unquoted_argument,
            self.get_space,
            self.get_newline,
            self.get_comment,
        ]
        for func in child_func:
            if child := func():
                return child

        return None

    def get_grouped_arguments(self):
        arguments = []
        lparen = r"\("
        rparen = r"\)"

        if match := self.eat_match(lparen):
            arguments.append(Token(match.pos, TokenKind.LParen, match.text))
        else:
            return None

        arguments.append(self.get_arguments())

        if match := self.eat_match(rparen):
            arguments.append(Token(match.pos, TokenKind.RParen, match.text))
        else:
            pos = rowcol(self.source, self.offset)
            raise SyntaxError(f"require closing ')' at {pos}")

        return GroupedArguments(arguments)

    def get_bracket(self) -> BracketTokens:
        children = []
        lbracket = r"\[=*\["
        rbracket = r"\]=*\]"
        text = r"(?:[^\]]|\\\])*"

        if match := self.eat_match(lbracket):
            children.append(Token(match.pos, TokenKind.LBracket, match.text))
        else:
            return None

        if match := self.eat_match(text):
            children.append(Token(match.pos, TokenKind.Text, match.text))

        if match := self.eat_match(rbracket):
            children.append(Token(match.pos, TokenKind.RBracket, match.text))
        else:
            pos = rowcol(self.source, self.offset)
            raise SyntaxError(f"require closing ']=*]' at {pos}")

        return BracketTokens(children)

    def get_bracket_argument(self) -> BracketArgument:
        if bracket := self.get_bracket():
            return BracketArgument(*bracket)
        return None

    def get_quoted_argument(self) -> QuotedArgument:
        children = []
        quote = r"\""
        text = rf"(?:\\{quote}|[^{quote}])+"

        if match := self.eat_match(quote):
            children.append(Token(match.pos, TokenKind.Quote, match.text))
        else:
            return None

        if match := self.eat_match(text):
            children.append(Token(match.pos, TokenKind.Text, match.text))

        if match := self.eat_match(quote):
            children.append(Token(match.pos, TokenKind.Quote, match.text))
        else:
            pos = rowcol(self.source, self.offset)
            raise SyntaxError(f"require closing '\"' at {pos}")

        return QuotedArgument(*children)

    def get_unquoted_argument(self) -> UnquotedArgument:
        # not implemented variable punctuation
        not_implemented = re.escape("${}<>;:")
        punctuation = re.escape('#[]()="\\')
        space = r" \t"
        newline = r"[\r\n]"
        escaped = rf"\\[{punctuation}{space}{newline}]"
        text = rf"(?:[^{punctuation}{space}]|{escaped}|{not_implemented})+"

        if match := self.eat_match(text):
            return UnquotedArgument(Token(match.pos, TokenKind.Text, match.text))
        else:
            return None

    def get_comment(self) -> Comment:
        comment_mark = r"#"
        if match := self.eat_match(comment_mark):
            comment_mark_token = Token(match.pos, TokenKind.CommentMark, match.text)

            if bracket := self.get_bracket():
                return BracketComment(comment_mark_token, *bracket)

            text = r".*"
            match_text = self.eat_match(text)
            text_token = Token(match_text.pos, TokenKind.Text, match_text.text)

            return LineComment(comment_mark_token, text_token)

        return None
