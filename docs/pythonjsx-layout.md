# PythonJSX layout conventions

Where new code should live in this project.

## `views.px`

HTTP entry points: parse the request, enforce permissions, choose status codes and
redirects, call selectors/services, return a `Page` or `JsonResponse`.

Keep views thin. No large HTML blocks that belong in components.

Large apps may split request-facing code into multiple `*_views.px` modules
when one `views.px` becomes too broad. Examples:

- `accounts/auth_views.px`, `registration_views.px`, `profile_views.px`,
  `home_views.px`
- `lists/editor_views.px`
- `problems/admin_views.px`, `export_views.px`
- `sources/admin_views.px`

Keep URL routing pointed at the specific module when possible. A small
compatibility `views.px` shim is acceptable during a transition.

## `components.px`

Reusable markup for one app area: tables, form sections, cards used on multiple
pages. May take models and `request`, but should not perform writes.

Use app-local `components.px` for markup that is specific to one app, such as
source archive tables or list index tables. Use `skoljka/components/` only for
cross-app primitives such as layout, pagination, form helpers, content editor,
and tag picker.

## `selectors.py`

Read-only query construction: `.for_user()` filters, prefetch plans, ordering,
aggregates. No `request` object. Shared by views, PDF export, and tests.

Prefer selectors for repeated visibility-sensitive query shapes, especially
when the same scope is used by page views and PDF/LaTeX export.

## Domain modules

Business logic that is not HTTP-specific and not pure querying:

- `archive_transfer.py`, `hierarchy.py`, `titles.py`, etc.
- Prefer functions with explicit inputs over reaching for `request`.

## `forms.py`

Django `Form` classes for POST validation and `save()`. Use for admin create/edit
flows instead of hand-parsing `request.POST`.

## Shared cross-app helpers

- `skoljka/components/` — layout, forms (`error_list`, `form_errors`, `csrf_input`)
- `skoljka/utils/` — auth decorators, staff checks, static URLs

## Staff accounts

`Model.objects.for_user(user)` returns **all** rows when `user.is_staff` is true.
Treat staff accounts like root: few accounts, strong passwords, 2FA if available.

Even in `@staff_required` views, use `.for_user(request.user, "edit")` for
edit/delete/import/export operations. This keeps the intent visible in code and
keeps the view correct if staff permissions become narrower later. Source
documents inherit source visibility, so destructive document operations should
scope through editable sources.

## TypeScript

Browser UI lives under `static/ts/`. Server-rendered pages pass JSON via
`<script type="application/json">` when needed. Prefer server-side ordering when
the API already provides sorted data (see PDF import sources).

Use `data-*` mount attributes for progressive enhancements. React-only workflows
use dedicated entrypoints such as `pdf-import.tsx` and `list-bulk-edit.tsx`.
