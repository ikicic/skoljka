# Component Architecture

This project uses server-rendered HTML first, then TypeScript enhances selected
parts of the page. Small form widgets should usually be progressive
enhancements: the server renders a real input/textarea/form, and TypeScript
adds richer behavior on top. Larger workflows such as the PDF import wizard and
bulk problem editor are React entrypoints and require JavaScript.

## Layers

### 1. PythonJSX Component (server-rendered)

A `.px` file in `skoljka/components/` or an app-local `components.px` file
renders the HTML. Shared UI belongs in `skoljka/components/`; app-specific
tables, sections, and cards belong next to that app.

```python
# skoljka/components/tag_picker.px
def TagPickerField(*, name: str, tags, selected_ids=None):
    selected_ids = set(selected_ids or [])
    selected_json = json.dumps(sorted(selected_ids))
    selected_names = ", ".join(t.name() for t in tags if t.pk in selected_ids)
    return (
        <div data-tag-picker=""
             data-selected={selected_json}
             data-name={name}>
            <input type="text" name={name} value={selected_names}
                   placeholder="Comma-separated tags..." />
        </div>
    )
```

Key rules:
- Use `data-*` attributes to pass configuration to the client.
- A `data-<component-name>` attribute (e.g., `data-content-editor`, `data-tag-picker`) marks the element for client-side enhancement.
- For progressive widgets, render native `<input>`, `<select>`, or
  `<textarea>` elements that submit correctly without JS.
- For React-only workflows, render a clearly scoped mount element and embed
  initial JSON in `<script type="application/json">`.

### 2. Client-Side Enhancement (auto-init)

A TypeScript module that finds marked elements and enhances them. Two patterns exist:

**Vanilla TS** (for simple enhancements):
```typescript
function initFoo(container: HTMLElement): void { ... }
document.querySelectorAll<HTMLElement>("[data-foo]").forEach(initFoo);
```

**React mount/hydration** (for complex interactive widgets like TagPicker):
```tsx
// static/ts/components/TagPicker.tsx
import { hydrateRoot } from "react-dom/client";
import { useState } from "react";

function mountTagPicker(el: HTMLElement) {
    // Read config from data attributes and hydrate the server-rendered widget.
    hydrateRoot(el, <ManagedTagPicker ... />);
}
```

Key rules:
- Import auto-init component modules in `static/ts/main.ts`.
- Components that can appear in HTMX responses should listen for
  `htmx:afterSwap` and re-initialize inside the swapped target.

### 3. React Component (for React-driven UIs)

A `.tsx` file in `static/ts/components/` that can be used directly in React apps (e.g., the PDF import wizard).

```tsx
// static/ts/components/TagPicker.tsx
export function TagPicker({ selected, onChange, inputName }: Props) { ... }
```

Key rules:
- Accept an `inputName` prop (optional). When set, render hidden `<input>` elements so the component works inside a `<form>`.
- The component should be a controlled component (value + onChange).

## File Structure

For a component called `FooBar`:

| File | Purpose |
|---|---|
| `skoljka/components/foo_bar.px` | PythonJSX server component |
| `static/ts/components/FooBar.tsx` | React component + auto-init |
| `static/css/components/foo-bar.css` | Styles (imported in `main.css`) |

The React component and auto-init logic usually live in the same `.tsx` file.
The component is exported for use in React apps, and auto-init code near the
bottom handles server-rendered elements. Import the file in `main.ts` to
activate auto-init.

React-only pages use top-level entrypoints instead:

| Entry point | Mount element | Notes |
|---|---|---|
| `static/ts/pdf-import.tsx` | `#pdf-import` | PDF upload/import wizard; helpers live in `static/ts/pdfImport/` |
| `static/ts/list-bulk-edit.tsx` | `#list-bulk-edit` | Bulk problem editor, optionally with PDF preview |

## Existing Components

| Component | Server (.px) | Client (.tsx/.ts) | Description |
|---|---|---|---|
| ContentEditor | `content_editor.px` | `ContentEditor.tsx` | Markdown+LaTeX textarea with live preview |
| TagPicker | `tag_picker.px` | `TagPicker.tsx` | Autocomplete tag selection with pills |
| ListProblemPicker | `lists/editor_views.px` | `ListProblemPicker.ts` | List item search/reorder/save UI |
| ProblemViewSwitcher | problem table/card markup | `ProblemViewSwitcher.ts` | Table/card display toggle |
| StatusCells | problem action placeholders | `StatusCells.ts` | Solved/bookmark/like status cell rendering |
| PdfExportPreview | PDF export form/preview | `PdfExportPreview.ts` | Keeps preview heading mode in sync |
| ResizableColumns | — | `ResizableColumns.tsx` | Two-pane layout with drag divider (React-only) |

## When to Use React vs Vanilla

- **Vanilla TS**: The enhancement is simple: row clicks, view toggles, status
  cell rendering, confirm-count forms, or similar event binding.
- **React**: The component has richer state: autocomplete, draft editing,
  previews, drag/reorder flows, uploads, or multi-step workflows.

## CSS

- Component styles go in `static/css/components/<name>.css`.
- Import in `static/css/main.css`.
- Use the same class names in both the PythonJSX and React versions.
