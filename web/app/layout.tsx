import type { Metadata } from "next";
import AuthProvider from "@/components/AuthProvider";
import "./globals.css";

export const metadata: Metadata = {
  title: "JohnnyBets - AI Sports Betting Analysis",
  description: "AI-powered sports betting analysis with real-time odds, arbitrage detection, and contextual prop analysis.",
  keywords: ["sports betting", "NFL", "NHL", "MLB", "arbitrage", "prop bets", "odds"],
  authors: [{ name: "JohnnyBets" }],
  openGraph: {
    title: "JohnnyBets - AI Sports Betting Analysis",
    description: "AI-powered sports betting analysis with real-time odds, arbitrage detection, and contextual prop analysis.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-terminal-bg">
        <AuthProvider>
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}

