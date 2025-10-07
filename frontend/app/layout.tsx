import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "NDA Reviewer - Edgewater",
  description: "Automated NDA redlining with Edgewater checklist",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}
