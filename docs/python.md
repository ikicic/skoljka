# Python guidelines

## argparse

- Use `add = parser.add_argument` shorthand.
- Use `argparse.ArgumentDefaultsHelpFormatter` to show defaults in `--help`.
- Parse in a standalone function that returns a **dataclass** (not `Namespace`).
- For subcommands, return a union of dataclasses (or a dataclass containing a union field).

```python
@dataclass
class DownloadArgs:
    filter: str | None
    force: bool

@dataclass
class TranscribeArgs:
    filter: str | None
    force: bool
    model: str

Args = DownloadArgs | TranscribeArgs

def parse_args(argv: list[str] | None = None) -> Args:
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    add = parser.add_argument
    ...
```

## Classmethods

For static factory methods, prefer returning `cls(...)` and `-> Self` instead of hard-coding the class name. This keeps subclassing correct.

## Django permissions

Models that inherit `PermissionModel` should be read through
`Model.objects.for_user(user)` in request-facing code. Use
`Model.objects.for_user(user, "edit")` for edit, delete, import, export, and
bulk-save operations, even inside `@staff_required` views.

Direct manager access is acceptable for object creation, uniqueness checks,
management commands, migrations, tests, and code that is intentionally operating
outside request visibility rules.

## Typing

Run `make typecheck` for TypeScript. For Python static checks, use:

```sh
basedpyright -p pyrightconfig.json
```

Checking types for PythonJSX `.px` files is not yet fully implemented, so prefer
checking regular `.py` modules and keeping `.px` annotations pragmatic.
