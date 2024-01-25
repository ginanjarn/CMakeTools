"""CMake formatter"""

import logging
from abc import ABC, abstractmethod

try:
    import cmake_ast as ast
except ImportError:
    from . import cmake_ast as ast

logger = logging.getLogger("cmake_formatter")
logger.setLevel(logging.DEBUG)
sh = logging.StreamHandler()
logger.addHandler(sh)


class Formatter(ABC):
    @abstractmethod
    def __init__(self, source: str):
        pass

    @abstractmethod
    def format_source(self) -> str:
        pass


class CMakeFormatter(Formatter):
    def __init__(self, source: str):
        self.source = source

    def format_source(self) -> str:
        parser = ast.CMakeParser(self.source)
        tree = parser.parse()
        formatted = self.format_file(tree)

        return formatted

    def normalize_newline(
        self, text: str, *, max_newline: int = 3, normalize_eof: bool = True
    ) -> str:
        temp = []
        newline_count = 0

        for line in text.splitlines():
            stripped = line.rstrip()  # strip tail 'space'

            if not stripped:
                newline_count += 1
                if newline_count > max_newline:
                    continue
            else:
                newline_count = 0

            temp.append(stripped)

        norm_text = "\n".join(temp)

        if (not temp) or (not normalize_eof):
            return norm_text

        return norm_text + "\n"

    def format_file(self, file: ast.File) -> str:
        children = file.children
        temp = []

        for index, child in enumerate(children):
            if child.kind == ast.TokenKind.EOF:
                break

            if child.kind == ast.TokenKind.Newline:
                temp.append(child.text)
                continue

            if child.kind == ast.TokenKind.Space:
                try:
                    next_child = children[index + 1]
                except IndexError:
                    # end of file
                    continue

                # discard trailing space before newline
                if next_child.kind == ast.TokenKind.Newline:
                    continue

                temp.append(child.text)
                continue

            if isinstance(child, ast.CommandInvocation):
                fmt = self.format_command(child)
                temp.append(fmt)
                continue

            if isinstance(child, ast.Comment):
                temp.append(child.text)
                continue

            raise ValueError(f"undefined rule for {child}")

        text = "".join(temp)
        return self.normalize_newline(text)

    def format_command(self, command: ast.CommandInvocation) -> str:
        children = command.children
        temp = []

        # grammar: <identifier><space*><arguments>

        if children[0].kind != ast.TokenKind.Identifier:
            raise ValueError("children[0] must ast.Identifier")

        temp.append(children[0].text)
        argument_index = 1

        if children[1].kind == ast.TokenKind.Space:
            argument_index = 2
            # insert single space
            temp.append(" ")

        fmt = self.format_arguments(children[argument_index])
        temp.append(fmt)

        text = "".join(temp)
        return text

    def format_arguments(self, arguments: ast.Arguments) -> str:
        temp = []

        # grammar: <lparen><(argument|separator)*><rparen>

        for index, argument in enumerate(arguments):
            if argument.kind in {
                ast.TokenKind.LParen,
                ast.TokenKind.RParen,
                ast.TokenKind.Newline,
            }:
                temp.append(argument.text)
                continue

            if argument.kind == ast.TokenKind.Space:
                prev_child = arguments[index - 1]

                if prev_child.kind == ast.TokenKind.Newline:
                    # keep indentation
                    temp.append(argument.text)
                    continue

                if prev_child.kind in {ast.TokenKind.LParen, ast.TokenKind.Space}:
                    continue

                next_child = arguments[index + 1]
                if next_child.kind == ast.TokenKind.RParen:
                    continue

                temp.append(" ")

                continue

            if isinstance(argument, ast.GroupedArguments):
                self.format_arguments(argument)
                continue

            # default write children
            temp.append(argument.text)

        text = "".join(temp)
        return self.normalize_newline(text, max_newline=1, normalize_eof=False)
