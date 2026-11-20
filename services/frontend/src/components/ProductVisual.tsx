import { CATEGORY_BADGES } from "@/lib/format";
import type { Category } from "@/lib/types";

const GLYPHS: Record<Category, string> = {
  FIGURINE: "♜",
  BLURAY: "◉",
  BD: "❡",
  BOARD_GAME: "⚄",
  GOODIES: "✦",
  FANZINE: "☾",
};

/** Placeholder visual (no product photos in the demo dataset), with a proper text alternative. */
export function ProductVisual({ name, category, size = "card" }: { name: string; category: Category; size?: "card" | "large" }) {
  return (
    <div className={`visual visual--${size} visual--${category.toLowerCase()}`} role="img" aria-label={`Visuel : ${name}`}>
      <span className="visual__glyph" aria-hidden="true">
        {GLYPHS[category]}
      </span>
      <span className="visual__label" aria-hidden="true">
        {CATEGORY_BADGES[category]}
      </span>
    </div>
  );
}
