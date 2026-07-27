import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL(
    process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000",
  ),
  title: {
    default: "Agent Goodput",
    template: "%s | Agent Goodput",
  },
  description:
    "Save tokens only when verified work survives. A quality-gated control layer for Codex.",
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
  },
  openGraph: {
    title: "Agent Goodput",
    description: "Spend less reasoning. Keep the result.",
    type: "website",
    images: [
      {
        url: "/og-card.png",
        width: 1200,
        height: 630,
        alt: "Agent Goodput synthetic benchmark dashboard showing 35 of 35 verified tasks and 29.8 percent fewer raw tokens.",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "Agent Goodput",
    description: "Spend less reasoning. Keep the result.",
    images: ["/og-card.png"],
  },
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
