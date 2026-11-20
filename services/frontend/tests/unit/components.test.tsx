import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ActiveFilters, CatalogFilters, Pagination } from "@/components/CatalogFilters";
import { ProductCard, ProductGrid } from "@/components/ProductCard";
import type { ProductSummary } from "@/lib/types";

const orc: ProductSummary = {
  id: "fig-orc-evil-ed",
  name: "Figurine L'Orc — édition collector",
  category: "FIGURINE",
  universe: "heroic-fantasy",
  price: 89,
  exclusiveEvilEd: true,
  imageUrl: null,
  stockByStore: { ANGOULEME: 5, AIX: 0, LYON: 0, LONDRES: 0, ONLINE: 20 },
};

describe("ProductCard", () => {
  it("renders an accessible card with a single link to the product", () => {
    render(<ProductCard product={orc} />);
    const link = screen.getByRole("link", { name: orc.name });
    expect(link).toHaveAttribute("href", "/produit/fig-orc-evil-ed");
    expect(screen.getByRole("heading", { level: 3, name: orc.name })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: `Visuel : ${orc.name}` })).toBeInTheDocument();
    expect(screen.getByText("Exclusivité Evil Ed")).toBeInTheDocument();
    expect(screen.getByText(/89,00/)).toBeInTheDocument();
    expect(screen.getAllByRole("link")).toHaveLength(1);
  });

  it("shows the category badge for regular products", () => {
    render(<ProductCard product={{ ...orc, exclusiveEvilEd: false, category: "BLURAY" }} />);
    expect(screen.getByText("Blu-ray", { selector: ".badge" })).toBeInTheDocument();
  });

  it("lists products in a labelled list", () => {
    render(<ProductGrid products={[orc, { ...orc, id: "other" }]} label="Nouveautés" />);
    expect(within(screen.getByRole("list", { name: "Nouveautés" })).getAllByRole("listitem")).toHaveLength(2);
  });
});

describe("CatalogFilters", () => {
  it("labels every control and reflects the current filters", () => {
    render(<CatalogFilters filters={{ category: "BD", store: "LYON", q: "orc" }} />);
    expect(screen.getByLabelText("Recherche")).toHaveValue("orc");
    expect(screen.getByLabelText("Bandes dessinées")).toBeChecked();
    expect(screen.getByLabelText("Lyon")).toBeChecked();
    expect(screen.getByRole("group", { name: "Catégories" })).toBeInTheDocument();
    expect(screen.getByRole("group", { name: "Disponible en magasin" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Appliquer les filtres" })).toBeInTheDocument();
  });

  it("offers a link to remove each active filter", () => {
    render(<ActiveFilters filters={{ category: "BD", q: "orc" }} />);
    expect(screen.getByRole("link", { name: /Bandes dessinées.*retirer/ })).toHaveAttribute("href", "/boutique?q=orc");
    expect(screen.getByRole("link", { name: "Tout effacer" })).toHaveAttribute("href", "/boutique");
  });

  it("renders nothing without active filter", () => {
    const { container } = render(<ActiveFilters filters={{}} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("marks the current page in the pagination", () => {
    render(<Pagination filters={{ category: "BD", page: 2 }} totalPages={3} />);
    const nav = screen.getByRole("navigation", { name: "Pagination" });
    expect(within(nav).getByRole("link", { name: "Page 2" })).toHaveAttribute("aria-current", "page");
    expect(within(nav).getByRole("link", { name: /Précédente/ })).toHaveAttribute("href", "/boutique?category=BD");
    expect(within(nav).getByRole("link", { name: /Suivante/ })).toHaveAttribute("href", "/boutique?category=BD&page=3");
  });

  it("hides pagination when there is a single page", () => {
    const { container } = render(<Pagination filters={{}} totalPages={1} />);
    expect(container).toBeEmptyDOMElement();
  });
});
