import { useEffect, useRef, useState } from "react";
import * as pdfjsLib from "pdfjs-dist/legacy/build/pdf.mjs";
import { gettext } from "../i18n";

pdfjsLib.GlobalWorkerOptions.workerSrc = "/static/vendor/pdfjs/pdf.worker.min.mjs";

export type PdfDocument = pdfjsLib.PDFDocumentProxy;

export async function renderPdfPage(
  pdfDoc: PdfDocument,
  pageNum: number,
  canvas: HTMLCanvasElement,
  targetWidth: number,
) {
  const page = await pdfDoc.getPage(pageNum);
  const viewport = page.getViewport({ scale: 1 });
  const scale = targetWidth / viewport.width;
  const scaled = page.getViewport({ scale });
  const pixelRatio = Math.max(1, window.devicePixelRatio || 1);
  canvas.width = Math.floor(scaled.width * pixelRatio);
  canvas.height = Math.floor(scaled.height * pixelRatio);
  canvas.style.width = `${Math.floor(scaled.width)}px`;
  canvas.style.height = `${Math.floor(scaled.height)}px`;
  const ctx = canvas.getContext("2d")!;
  await page.render({
    canvasContext: ctx,
    viewport: scaled,
    transform: pixelRatio === 1 ? undefined : [pixelRatio, 0, 0, pixelRatio, 0, 0],
  } as any).promise;
}

export function PdfPageCanvas({
  pdfDoc,
  pageNum,
  targetWidth = 1200,
}: {
  pdfDoc: PdfDocument;
  pageNum: number;
  targetWidth?: number;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (canvasRef.current) {
      renderPdfPage(pdfDoc, pageNum, canvasRef.current, targetWidth);
    }
  }, [pdfDoc, pageNum, targetWidth]);

  return <canvas ref={canvasRef} className="pdf-page-canvas" />;
}

export function PdfDocumentPreview({ url }: { url: string; label?: string }) {
  const [pdfDoc, setPdfDoc] = useState<PdfDocument | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    let loadedDoc: PdfDocument | null = null;
    setPdfDoc(null);
    setError("");

    const task = pdfjsLib.getDocument(url);
    task.promise
      .then((doc) => {
        if (cancelled) {
          void doc.destroy();
          return;
        }
        loadedDoc = doc;
        setPdfDoc(doc);
      })
      .catch(() => {
        if (!cancelled) setError(gettext("PDF could not be loaded."));
      });

    return () => {
      cancelled = true;
      if (loadedDoc) void loadedDoc.destroy();
      else void task.destroy();
    };
  }, [url]);

  if (error) return <p className="text-muted">{error}</p>;
  if (!pdfDoc) return <p className="text-muted">{gettext("Loading PDF...")}</p>;

  return (
    <>
      {Array.from({ length: pdfDoc.numPages }, (_, index) => (
        <PdfPageCanvas key={index + 1} pdfDoc={pdfDoc} pageNum={index + 1} />
      ))}
    </>
  );
}
