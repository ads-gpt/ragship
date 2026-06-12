import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Ragship",
  description: "Ask AdventureWorks questions and inspect generated SQL.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
