import type { Metadata, Viewport } from "next";
import { Cinzel, Creepster, Inter } from "next/font/google";

import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";
import { getRequestContext } from "@/lib/viewer";

import "./globals.css";

// Self-hosted at build time by next/font: no request to Google from the visitor's browser (GDPR, CSP font-src 'self').
const cinzel = Cinzel({ subsets: ["latin"], weight: ["400", "600", "700"], variable: "--font-title", display: "swap" });
const inter = Inter({ subsets: ["latin"], variable: "--font-text", display: "swap" });
const creepster = Creepster({ subsets: ["latin"], weight: "400", variable: "--font-logo", display: "swap" });

export const metadata: Metadata = {
  title: { default: "La Petite Maison de l'Épouvante", template: "%s · La Petite Maison de l'Épouvante" },
  description: "Figurines, films, BD, jeux de société et fanzine horreur & fantastique.",
};

export const viewport: Viewport = { themeColor: "#0E0B0D", colorScheme: "dark" };

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const { viewer, pathname } = await getRequestContext();
  return (
    <html lang="fr" className={`${cinzel.variable} ${inter.variable} ${creepster.variable}`}>
      <body>
        <a href="#contenu" className="skip-link">
          Aller au contenu
        </a>
        <Header viewer={viewer} returnTo={pathname} />
        <main id="contenu" tabIndex={-1}>
          {children}
        </main>
        <Footer />
      </body>
    </html>
  );
}
