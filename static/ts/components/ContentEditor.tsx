/**
 * ContentEditor — Markdown + LaTeX editor with live preview.
 *
 * Used in two ways:
 *   1. As a React component in React apps (e.g. PDF import).
 *   2. Auto-initialized on server-rendered [data-content-editor] elements.
 *
 * The server-rendered markup includes a real textarea, so forms submit
 * correctly before this component is loaded.
 */

import { createRoot } from "react-dom/client";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { compileMarkdown } from "../content-markdown";
import { gettext, interpolate } from "../i18n";

type Layout = "vertical" | "horizontal";
type VerticalOrder = "source-preview" | "preview-source";

interface Props {
  value: string;
  onChange: (value: string) => void;
  name?: string;
  id?: string;
  rows?: number;
  placeholder?: string;
  layout?: Layout;
  debounceMs?: number;
  className?: string;
  textareaClassName?: string;
  previewClassName?: string;
  verticalOrder?: VerticalOrder;
  submitLabel?: string;
  submitClassName?: string;
  showFormatHelp?: boolean;
  attachments?: Attachment[];
  uploadName?: string;
  contentId?: string;
}

interface Attachment {
  name: string;
  url: string;
  is_image?: boolean;
}

interface UploadResponse {
  attachments?: Attachment[];
  error?: string;
}

interface AttachmentDragPayload {
  contentId: string;
  name: string;
}

const EMPTY_ATTACHMENTS: Attachment[] = [];
const ATTACHMENT_DRAG_TYPE = "application/x-skoljka-attachment";

function imageSnippet(name: string): string {
  return `![figure](attachment:${name}){width=50%}`;
}

function insertTextAtCursor(textarea: HTMLTextAreaElement, text: string): void {
  textarea.focus();
  if (document.queryCommandSupported?.("insertText")) {
    document.execCommand("insertText", false, text);
  } else {
    textarea.setRangeText(text, textarea.selectionStart, textarea.selectionEnd, "end");
    textarea.dispatchEvent(new InputEvent("input", { bubbles: true }));
  }
}

function csrfTokenFor(el: HTMLElement | null): string {
  const input = el
    ?.closest("form")
    ?.querySelector<HTMLInputElement>('input[name="csrfmiddlewaretoken"]');
  return input?.value || "";
}

function canPatchNode(current: Node, next: Node): boolean {
  if (current.nodeType !== next.nodeType) return false;
  if (current.nodeType !== Node.ELEMENT_NODE) return true;
  return (
    (current as Element).tagName.toLowerCase() ===
    (next as Element).tagName.toLowerCase()
  );
}

function syncAttributes(current: Element, next: Element): void {
  for (const attr of Array.from(current.attributes)) {
    if (!next.hasAttribute(attr.name)) current.removeAttribute(attr.name);
  }

  for (const attr of Array.from(next.attributes)) {
    if (current.getAttribute(attr.name) !== attr.value) {
      current.setAttribute(attr.name, attr.value);
    }
  }
}

function morphNode(current: Node, next: Node): void {
  if (!canPatchNode(current, next)) {
    current.parentNode?.replaceChild(next.cloneNode(true), current);
    return;
  }

  if (current.nodeType === Node.TEXT_NODE) {
    if (current.nodeValue !== next.nodeValue) current.nodeValue = next.nodeValue;
    return;
  }

  if (current.nodeType === Node.ELEMENT_NODE) {
    syncAttributes(current as Element, next as Element);
    morphChildren(current, next);
  }
}

function morphChildren(currentParent: Node, nextParent: Node): void {
  const nextChildren = Array.from(nextParent.childNodes);
  let current = currentParent.firstChild;

  for (const next of nextChildren) {
    if (!current) {
      currentParent.appendChild(next.cloneNode(true));
      continue;
    }

    const following = current.nextSibling;
    morphNode(current, next);
    current = following;
  }

  while (current) {
    const following = current.nextSibling;
    current.parentNode?.removeChild(current);
    current = following;
  }
}

function updatePreviewHtml(preview: HTMLElement, html: string): void {
  const template = document.createElement("template");
  template.innerHTML = html;
  morphChildren(preview, template.content);
}

export function ContentEditor({
  value,
  onChange,
  name,
  id,
  rows,
  placeholder = gettext("Markdown + LaTeX"),
  layout = "horizontal",
  debounceMs = 50,
  className = "",
  textareaClassName = "",
  previewClassName = "",
  verticalOrder = "source-preview",
  submitLabel = "",
  submitClassName = "btn btn-sm",
  showFormatHelp = false,
  attachments = EMPTY_ATTACHMENTS,
  uploadName,
  contentId,
}: Props) {
  const [attachmentItems, setAttachmentItems] = useState(attachments);
  const [isDraggingFiles, setIsDraggingFiles] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const attachmentUrls = useMemo(
    () =>
      Object.fromEntries(
        attachmentItems.map((attachment) => [attachment.name, attachment.url]),
      ),
    [attachmentItems],
  );
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const stackRef = useRef<HTMLDivElement>(null);
  const sourceRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const previewRef = useRef<HTMLDivElement>(null);
  const hasRenderedPreviewRef = useRef(false);

  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    const render = () => {
      if (previewRef.current) {
        updatePreviewHtml(previewRef.current, compileMarkdown(value, attachmentUrls));
        hasRenderedPreviewRef.current = true;
      }
    };
    if (hasRenderedPreviewRef.current) {
      timerRef.current = setTimeout(render, debounceMs);
    } else {
      render();
    }
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [value, debounceMs, attachmentUrls]);

  useEffect(() => {
    setAttachmentItems(attachments);
  }, [attachments]);

  const onDividerMouseDown = useCallback(
    (e: React.MouseEvent) => {
      if (layout !== "vertical") return;
      e.preventDefault();
      const stack = stackRef.current;
      const source = sourceRef.current;
      if (!stack || !source) return;

      const startX = e.clientX;
      const startWidth = source.getBoundingClientRect().width;

      function onMouseMove(ev: MouseEvent) {
        const stackWidth = stack!.getBoundingClientRect().width;
        const pct = Math.max(
          25,
          Math.min(70, ((startWidth + ev.clientX - startX) / stackWidth) * 100),
        );
        stack!.style.setProperty("--content-editor-source-width", `${pct}%`);
      }

      function onMouseUp() {
        document.removeEventListener("mousemove", onMouseMove);
        document.removeEventListener("mouseup", onMouseUp);
        document.body.style.cursor = "";
        document.body.style.userSelect = "";
      }

      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";
      document.addEventListener("mousemove", onMouseMove);
      document.addEventListener("mouseup", onMouseUp);
    },
    [layout],
  );

  const appendImage = useCallback(
    (name: string) => {
      const textarea = textareaRef.current;
      if (!textarea) return;
      const snippet = imageSnippet(name);
      const endOfText = textarea.value.length;
      const prefix = textarea.value;
      const spacerBefore = prefix && !prefix.endsWith("\n") ? "\n\n" : "";
      const text = `${spacerBefore}${snippet}`;

      textarea.setSelectionRange(endOfText, endOfText);
      insertTextAtCursor(textarea, text);
    },
    [],
  );

  const deleteAttachment = useCallback(
    async (name: string) => {
      if (!contentId) {
        return;
      }
      if (!window.confirm(interpolate(
          gettext('Delete attachment "%(name)s"?'), { name }))) {
        return;
      }

      try {
        const response = await fetch(
          `/content/${encodeURIComponent(contentId)}/attachments/${encodeURIComponent(name)}/`,
          {
            method: "DELETE",
            headers: { "X-CSRFToken": csrfTokenFor(stackRef.current) },
          },
        );
        if (!response.ok) {
          window.alert(gettext("Deleting the attachment failed."));
          return;
        }
      } catch {
        window.alert(gettext("Deleting the attachment failed."));
        return;
      }
      setAttachmentItems((items) => items.filter((item) => item.name !== name));
    },
    [contentId],
  );

  const uploadFiles = useCallback(
    async (files: FileList | File[]) => {
      if (!contentId || files.length === 0) return;

      const formData = new FormData();
      Array.from(files).forEach((file) => formData.append("files", file));
      setIsUploading(true);
      try {
        const response = await fetch(
          `/content/${encodeURIComponent(contentId)}/attachments/`,
          {
            method: "POST",
            headers: { "X-CSRFToken": csrfTokenFor(stackRef.current) },
            body: formData,
          },
        );
        const payload = (await response.json().catch(() => ({}))) as UploadResponse;
        if (!response.ok || !payload.attachments) {
          window.alert(payload.error || gettext("Uploading attachments failed."));
          return;
        }
        setAttachmentItems((items) => [...items, ...payload.attachments!]);
      } catch {
        window.alert(gettext("Uploading attachments failed."));
      } finally {
        setIsUploading(false);
      }
    },
    [contentId],
  );

  const onUploadChange = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      if (event.target.files) void uploadFiles(event.target.files);
      event.target.value = "";
    },
    [uploadFiles],
  );

  const onDragOver = useCallback((event: React.DragEvent) => {
    if (!contentId || event.dataTransfer.types.includes("Files") === false) return;
    event.preventDefault();
    setIsDraggingFiles(true);
  }, [contentId]);

  const onDragLeave = useCallback((event: React.DragEvent) => {
    if (!event.currentTarget.contains(event.relatedTarget as Node | null)) {
      setIsDraggingFiles(false);
    }
  }, []);

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      if (!contentId) return;
      event.preventDefault();
      setIsDraggingFiles(false);
      void uploadFiles(event.dataTransfer.files);
    },
    [contentId, uploadFiles],
  );

  const onTextareaDragOver = useCallback((event: React.DragEvent<HTMLTextAreaElement>) => {
    if (!event.dataTransfer.types.includes(ATTACHMENT_DRAG_TYPE)) return;
    event.preventDefault();
    event.dataTransfer.dropEffect = "copy";
  }, []);

  const onTextareaDrop = useCallback(
    (event: React.DragEvent<HTMLTextAreaElement>) => {
      const raw = event.dataTransfer.getData(ATTACHMENT_DRAG_TYPE);
      if (!raw) return;

      event.preventDefault();
      let payload: AttachmentDragPayload;
      try {
        payload = JSON.parse(raw) as AttachmentDragPayload;
      } catch {
        return;
      }

      if (payload.contentId !== contentId) {
        window.alert(gettext("This attachment belongs to a different content item."));
        return;
      }

      insertTextAtCursor(event.currentTarget, imageSnippet(payload.name));
    },
    [contentId],
  );

  return (
    <div
      ref={stackRef}
      className={`content-editor content-editor-${layout} content-editor-${verticalOrder} ${className}`.trim()}
      style={
        layout === "vertical"
          ? ({ "--content-editor-source-width": "44%" } as React.CSSProperties)
          : undefined
      }
    >
      <div ref={sourceRef} className="content-editor-panel content-editor-source">
        <textarea
          ref={textareaRef}
          name={name}
          id={id}
          rows={rows}
          placeholder={placeholder}
          className={`content-editor-textarea ${textareaClassName}`.trim()}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onDragOver={onTextareaDragOver}
          onDrop={onTextareaDrop}
        />
      </div>
      {layout === "vertical" && (
        <div className="resize-divider" onMouseDown={onDividerMouseDown} />
      )}
      {(submitLabel || showFormatHelp) && (
        <div className="content-editor-actions">
          {submitLabel && (
            <button type="submit" className={submitClassName}>
              {submitLabel}
            </button>
          )}
          {showFormatHelp && (
            <a href="/help/format/" target="_blank" rel="noopener">
              {gettext("Input format help")}
            </a>
          )}
        </div>
      )}
      <div className="content-editor-panel content-editor-rendered">
        <div
          ref={previewRef}
          className={`content-editor-preview math-content ${previewClassName}`.trim()}
        />
      </div>
      {contentId && (attachmentItems.length > 0 || uploadName) && (
        <div
          className={`content-editor-attachments${isDraggingFiles ? " dragging" : ""}`.trim()}
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          onDrop={onDrop}
        >
          {attachmentItems.length > 0 && (
            <table className="content-editor-attachment-list">
              <tbody>
              {attachmentItems.map((attachment) => (
                <AttachmentRow
                  key={attachment.name}
                  attachment={attachment}
                  contentId={contentId}
                  onAppendImage={appendImage}
                  onDelete={deleteAttachment}
                />
              ))}
              </tbody>
            </table>
          )}
          {uploadName && (
            <label className="content-editor-upload">
              <span>{isUploading ? gettext("Uploading...") : gettext("Upload attachments")}</span>
              <input
                type="file"
                name={uploadName}
                multiple
                disabled={isUploading}
                onChange={onUploadChange}
              />
            </label>
          )}
        </div>
      )}
    </div>
  );
}

function AttachmentRow({
  attachment,
  contentId,
  onAppendImage,
  onDelete,
}: {
  attachment: Attachment;
  contentId: string;
  onAppendImage: (name: string) => void;
  onDelete: (name: string) => void;
}) {
  const onDragStart = useCallback(
    (event: React.DragEvent) => {
      if (!attachment.is_image) {
        event.preventDefault();
        return;
      }

      const snippet = imageSnippet(attachment.name);
      const payload: AttachmentDragPayload = {
        contentId,
        name: attachment.name,
      };
      event.dataTransfer.effectAllowed = "copy";
      event.dataTransfer.setData(ATTACHMENT_DRAG_TYPE, JSON.stringify(payload));
      event.dataTransfer.setData("text/plain", snippet);
    },
    [attachment.is_image, attachment.name, contentId],
  );

  return (
    <tr
      className="content-editor-attachment"
      draggable={!!attachment.is_image}
      onDragStart={onDragStart}
    >
      <td className="content-editor-attachment-icon">
        {attachment.is_image ? (
          <img
            src={attachment.url}
            alt=""
            className="content-editor-attachment-thumb"
          />
        ) : (
          <span className="content-editor-attachment-file">{gettext("file")}</span>
        )}
      </td>
      <td className="content-editor-attachment-name">
        <a href={attachment.url} target="_blank">{attachment.name}</a>
      </td>
      <td className="content-editor-attachment-action">
        {attachment.is_image && (
          <button
            type="button"
            className="btn btn-sm content-editor-insert-attachment"
            onClick={() => onAppendImage(attachment.name)}
          >
            {gettext("Append to text")}
          </button>
        )}
      </td>
      <td className="content-editor-attachment-action">
        {/* TODO: btn-danger or something like that */}
        <button
          type="button"
          className="btn btn-sm"
          onClick={() => onDelete(attachment.name)}
        >
          {gettext("Delete")}
        </button>
      </td>
    </tr>
  );
}

function ManagedContentEditor({
  initialValue,
  ...props
}: Omit<Props, "value" | "onChange"> & { initialValue: string }) {
  const [value, setValue] = useState(initialValue);
  return <ContentEditor {...props} value={value} onChange={setValue} />;
}

function mountContentEditor(el: HTMLElement) {
  if (el.dataset.contentEditorMounted === "1") return;

  const textarea = el.querySelector<HTMLTextAreaElement>("textarea");
  if (!textarea) return;
  el.dataset.contentEditorMounted = "1";
  const attachments = JSON.parse(el.dataset.attachments || "[]") as Attachment[];
  const contentId = el.dataset.contentId || undefined;

  createRoot(el).render(
    <ManagedContentEditor
      initialValue={textarea.value}
      name={textarea.name}
      id={textarea.id || undefined}
      rows={textarea.rows || undefined}
      placeholder={textarea.placeholder || undefined}
      layout={(el.dataset.layout as Layout | undefined) || "horizontal"}
      className={el.dataset.className || undefined}
      previewClassName={el.dataset.previewClassName || undefined}
      verticalOrder={(el.dataset.verticalOrder as VerticalOrder | undefined) || undefined}
      submitLabel={el.dataset.submitLabel || undefined}
      submitClassName={el.dataset.submitClassName || undefined}
      showFormatHelp={el.dataset.showFormatHelp === "1"}
      attachments={attachments}
      uploadName={el.dataset.uploadName || undefined}
      contentId={contentId}
    />,
  );
}

function initAllContentEditors(root: ParentNode = document) {
  if (root instanceof HTMLElement && root.matches("[data-content-editor]")) {
    mountContentEditor(root);
  }
  root
    .querySelectorAll<HTMLElement>("[data-content-editor]")
    .forEach(mountContentEditor);
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => initAllContentEditors());
} else {
  initAllContentEditors();
}

document.addEventListener("htmx:afterSwap", (event: Event) => {
  const target = (event as CustomEvent).detail?.target;
  if (target instanceof HTMLElement) {
    initAllContentEditors(target);
  }
});
