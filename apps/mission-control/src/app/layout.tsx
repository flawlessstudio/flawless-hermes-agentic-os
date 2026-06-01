import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Hermes Mission Control",
  description: "Agent OS Mission Control Dashboard",
  robots: "noindex, nofollow",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#0a0a0f",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <a
          href="#main-content"
          className="sr-only"
          style={{
            background: "var(--color-accent)",
            color: "white",
            padding: "0.5rem 1rem",
            borderRadius: "var(--radius-md)",
          }}
        >
          Skip to main content
        </a>
        {children}
      </body>
    </html>
  );
}
