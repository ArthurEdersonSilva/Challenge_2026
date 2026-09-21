import sys
import unittest
from pathlib import Path


def main():
    raiz = Path(__file__).resolve().parent
    suite = unittest.defaultTestLoader.discover(
        str(raiz / "tests"),
        pattern="test_evidencias_services.py",
    )
    resultado = unittest.TextTestRunner(
        verbosity=2,
    ).run(suite)
    sys.exit(0 if resultado.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
