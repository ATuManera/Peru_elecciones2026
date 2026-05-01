from __future__ import annotations

import argparse

AUTHOR_ORGANIZATION = "A Tu Manera Digital"
AUTHOR_NAME = "Fernando Gallarday"
ASSISTED_COAUTHORS = ("Claude Opus 4.6", "GPT-5.5", "Claude Sonnet 4.6")
CREATED_DATE = "viernes 17 abril 2026"
LICENSE_NAME = "Apache-2.0"


def build_help_epilog(assisted_coauthors: tuple[str, ...] = ASSISTED_COAUTHORS) -> str:
    return (
        f"Autor: {AUTHOR_ORGANIZATION} - {AUTHOR_NAME}\n"
        f"Fecha de creación: {CREATED_DATE}\n"
        f"Co-autoría asistida por modelos: {', '.join(assisted_coauthors)}\n"
        f"Licencia: {LICENSE_NAME}"
    )


HELP_EPILOG = build_help_epilog()


def build_argument_parser(*args, **kwargs) -> argparse.ArgumentParser:
    assisted_coauthors = kwargs.pop("assisted_coauthors", ASSISTED_COAUTHORS)
    if "epilog" not in kwargs:
        kwargs["epilog"] = build_help_epilog(assisted_coauthors)
    kwargs.setdefault("formatter_class", argparse.RawDescriptionHelpFormatter)
    return argparse.ArgumentParser(*args, **kwargs)
