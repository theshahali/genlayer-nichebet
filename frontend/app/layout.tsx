import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'NicheBet — Autonomous Long-Tail & P2P Prediction Markets',
  description: 'Bet on anything online. Resolved in 60s by decentralized GenLayer AI consensus.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-[#080c14] text-slate-100 min-h-screen antialiased font-mono">
        {children}
      </body>
    </html>
  );
}
