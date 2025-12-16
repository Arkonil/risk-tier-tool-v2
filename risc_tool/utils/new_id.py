import typing as t


def id_generator() -> t.Generator[int, None, None]:
    current = 0
    while True:
        current += 1
        yield current


def new_id(
    gen: t.Generator[int, None, None], current_ids: t.Collection[int] | None = None
) -> int:
    if current_ids is None:
        current_ids = []

    while True:
        new_id = next(gen)
        if new_id not in current_ids:
            return new_id


__all__ = ["new_id"]
