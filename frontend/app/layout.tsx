import type { Metadata } from "next";
import "./globals.css";
import { ClientOnly } from "@/components/client-only";

export const metadata: Metadata = { title: "Echo Chamber", description: "Decision intelligence with a memory for outcomes." };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  // Some browser extensions annotate DOM nodes before React hydrates localhost pages.
  return <html lang="en" suppressHydrationWarning><body suppressHydrationWarning><ClientOnly>{children}</ClientOnly></body></html>;
}
