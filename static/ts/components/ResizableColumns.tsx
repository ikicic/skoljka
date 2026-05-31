import { useCallback, useRef, type ReactNode } from "react";

interface Props {
  left: ReactNode;
  right: ReactNode;
  initialLeftPercent?: number;
  minPercent?: number;
  maxPercent?: number;
  className?: string;
  leftClassName?: string;
  rightClassName?: string;
}

export function ResizableColumns({
  left,
  right,
  initialLeftPercent = 30,
  minPercent = 10,
  maxPercent = 70,
  className = "",
  leftClassName = "",
  rightClassName = "",
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const leftRef = useRef<HTMLDivElement>(null);

  const onMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      const container = containerRef.current;
      const leftEl = leftRef.current;
      if (!container || !leftEl) return;

      const startX = e.clientX;
      const startWidth = leftEl.getBoundingClientRect().width;

      function onMouseMove(ev: MouseEvent) {
        const containerWidth = container!.getBoundingClientRect().width;
        const newWidth = startWidth + ev.clientX - startX;
        const pct = Math.max(
          minPercent,
          Math.min(maxPercent, (newWidth / containerWidth) * 100),
        );
        container!.style.setProperty("--pdf-left-width", `${pct}%`);
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
    [minPercent, maxPercent],
  );

  return (
    <div
      ref={containerRef}
      className={`pdf-review-columns ${className}`}
      style={{ "--pdf-left-width": `${initialLeftPercent}%` } as React.CSSProperties}
    >
      <div
        ref={leftRef}
        className={`pdf-col ${leftClassName}`}
      >
        {left}
      </div>
      <div className="resize-divider" onMouseDown={onMouseDown} />
      <div className={`pdf-col ${rightClassName}`}>
        {right}
      </div>
    </div>
  );
}
