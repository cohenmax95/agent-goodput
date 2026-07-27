import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL(
    process.env.NEXT_PUBLIC_SITE_URL ?? "https://agent-goodput.netlify.app",
  ),
  title: {
    default: "Agent Goodput",
    template: "%s | Agent Goodput",
  },
  description:
    "Quality-gated token routing for Codex, with public benchmark evidence and automatic rollback.",
  alternates: {
    canonical: "/",
  },
  robots: {
    index: true,
    follow: true,
  },
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
  },
  openGraph: {
    title: "Agent Goodput",
    description:
      "Measured token routing with task-specific quality gates and public benchmark evidence.",
    type: "website",
    url: "/",
    images: [
      {
        url: "/og.png",
        width: 1731,
        height: 909,
        alt: "Agent Goodput benchmark card showing 35 of 35 verified tasks, 29.8 percent fewer raw tokens, and the rule that failed tasks score zero.",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "Agent Goodput",
    description:
      "Measured token routing with task-specific quality gates and public benchmark evidence.",
    images: ["/og.png"],
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
