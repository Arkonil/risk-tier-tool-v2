import typing as t


def id_generator() -> t.Generator[str, None, None]:
    current = 0
    while True:
        current += 1
        yield str(current)


def new_id(
    gen: t.Generator[str, None, None], current_ids: t.Collection[str] | None = None
) -> str:
    if current_ids is None:
        current_ids = []

    while True:
        new_id = str(next(gen))
        if new_id not in current_ids:
            return new_id


__all__ = ["new_id"]
