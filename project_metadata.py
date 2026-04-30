from __future__ import annotations

import argparse

AUTHOR_ORGANIZATION = "A Tu Manera Digital"
AUTHOR_NAME = "Fernando Gallarday"
ASSISTED_COAUTHORS = ("Opus 4.6", "ChatGPT 5.5", "Sonnet 4.6")
CREATED_DATE = "viernes 17 abril 2026"
LICENSE_NAME = "Apache-2.0"

HELP_EPILOG = (
    f"Autor: {AUTHOR_ORGANIZATION} - {AUTHOR_NAME}\n"
    f"Fecha de creación: {CREATED_DATE}\n"
    f"Co-autoría asistida por modelos: {', '.join(ASSISTED_COAUTHORS)}\n"
    f"Licencia: {LICENSE_NAME}"
)


def build_argument_parser(*args, **kwargs) -> argparse.ArgumentParser:
    kwargs.setdefault("epilog", HELP_EPILOG)
    kwargs.setdefault("formatter_class", argparse.RawDescriptionHelpFormatter)
    return argparse.ArgumentParser(*args, **kwargs)
