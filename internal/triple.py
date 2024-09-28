"""target triple helper
"""

import re
from dataclasses import dataclass
from typing import List


@dataclass
class TargetTriple:
    triple: str
    target_os: str
    target_arch: str
    vendors: List[str]
    abi: str
    libc: str

    def __str__(self):
        return self.to_string(self)

    @staticmethod
    def to_string(target: "TargetTriple") -> str:
        """"""

        triples = []
        if target.vendors:
            triples.append("_".join(target.vendors))
        if target.abi:
            triples.append(target.abi)
        if target.libc:
            triples.append(target.libc)
        return "-".join(triples)


class TargetTripleParser:
    """"""

    def __init__(self, text: str):
        self.text = text

    def parse(self) -> TargetTriple:
        target_triple = self._find_target_triple(self.text)
        return self._parse_target_triple(target_triple)

    @staticmethod
    def _find_target_triple(lines: str) -> str:
        """find target triple from text"""

        for line in lines.splitlines():
            if match := re.match(r"^Target:\s+(.*)", line):
                return match.group(1)

            if match := re.match(r".*gcc-lib[/\\]([^/\\]*)[/\\]", line):
                return match.group(1)

        return ""

    @staticmethod
    def _parse_target_triple(triple: str) -> TargetTriple:
        """"""

        triples = triple.split("-")
        found_arch = "unknown"
        found_os = "unknown"
        found_abi = "unknown"
        found_libc = "unknown"
        element_to_skip = []

        for element in triples:
            for key, pattern in _possibly_arch.items():
                if re.match(pattern, element):
                    element_to_skip.append(key)
                    found_arch = key
                    break

            for key, pattern in _possibly_os.items():
                if re.match(pattern, element):
                    element_to_skip.append(key)
                    if found_os == "unknown" or key == "none":
                        # os other than none have higher priority
                        # so we not break
                        found_os = key

            for key, pattern in _possibly_abi.items():
                if re.match(pattern, element):
                    element_to_skip.append(key)
                    found_abi = key
                    break

            for key, pattern in _possibly_libc.items():
                if re.match(pattern, element):
                    element_to_skip.append(key)
                    found_libc = key
                    break

        vendors = []
        for element in triples:
            if element in element_to_skip:
                vendors.append(element)

        return TargetTriple(
            triple=triple,
            target_os=found_os if found_os != "unknown" else "none",
            target_arch=found_arch,
            vendors=vendors,
            abi=found_abi if found_abi != "unknown" else "",
            libc=found_libc if found_libc != "unknown" else "",
        )


_possibly_arch = {
    "x86": r"^(i386|i486|i586|i686|x86)$",
    "aarch64": r"^aarch64.*",
    "amdgcn": r"^amdgcn",
    "arc": r"^arc",
    "arm": r"^arm",
    "avr": r"^avr",
    "blackfin": r"^blackfin",
    "cr16": r"^cr16",
    "cris": r"^cris",
    "epiphany": r"^epiphany",
    "h8300": r"^h8300",
    "hppa": r"^hppa.*",
    "ia64": r"^ia64",
    "iq2000": r"^iq2000",
    "lm32": r"^lm32",
    "m32c": r"^m32c",
    "m32r": r"^m32r",
    "m68k": r"^m68k",
    "microblaze": r"^microblaze",
    "mips": r"^mips",
    "moxie": r"^moxie",
    "msp430": r"^msp430",
    "nds32le": r"^nds32le",
    "nds32be": r"^nds32be",
    "nvptx": r"^nvptx",
    "or1k": r"^or1k",
    "powerpc": r"^powerpc$",
    "powerpcle": r"^powerpcle$",
    "rl78": r"^rl78",
    "riscv32": r"^riscv32",
    "riscv64": r"^riscv64",
    "rx": r"^rx",
    "s390": r"^s390$",
    "s390x": r"^s390x$",
    "sparc": r"^sparc$",
    "sparc64": r"^(sparc64|sparcv9)$",
    "c6x": r"^c6x$",
    "tilegx": r"^tilegx$",
    "tilegxbe": r"^tilegxbe$",
    "tilepro": r"^tilepro$",
    "visium": r"^visium",
    "x64": r"^(x86_64|amd64|x64)$",
    "xtensa": r"^xtensa.*",
}

_possibly_os = {
    "win32": r"^(mingw32|mingw|mingw64|w64|msvc|windows)",
    "cygwin": r"^cygwin",
    "msys": r"^msys",
    "linux": r"^linux.*",
    "solaris": r"^solaris.*",
    "darwin": r"^darwin.*",
    "uclinux": r"^uclinux.*",
    "bsd": r"^(netbsd|openbsd)",
    "vxworks": r"^(vxworks|vxworksae)$",
    "none": r"^none$",
}

_possibly_abi = {
    "elf": r"^(linux.*|uclinux.*|elf|netbsd|openbsd|aix|solaris.*|gnueabi|gnueabihf)",
    "marcho": r"^darwin.*",
    "pe": r"^(mingw32|mingw|mingw64|w64|msvc|windows|cygwin|msys)",
    "eabi": r"^eabi$",
    "eabisim": r"^eabisim$",
}

_possibly_libc = {
    "mingw": r"^(mingw32|mingw|mingw64|w64)",
    "musl": r"^musl$",
    "glibc": r"^(gnu|msys|cygwin)$",
    "msvcrt": r"^msvc$",
}
