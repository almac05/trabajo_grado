"""Utilidades compartidas para el pipeline ETL."""

try:
    from IPython.display import display  # type: ignore
except ImportError:  # pragma: no cover

    def display(obj):  # type: ignore
        print(obj)
