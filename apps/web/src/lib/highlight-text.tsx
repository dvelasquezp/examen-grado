import type { ReactNode } from "react";

export function highlightTerm(text: string, term: string | null): ReactNode[] {
  if (!term?.trim()) {
    return [text];
  }

  const escaped = term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const pattern = new RegExp(`(${escaped})`, "gi");
  const parts = text.split(pattern);

  return parts.map((part, i) => {
    if (part.toLowerCase() === term.toLowerCase()) {
      return (
        <mark key={i} className="bg-yellow-200 rounded px-0.5">
          {part}
        </mark>
      );
    }
    return <span key={i}>{part}</span>;
  });
}
