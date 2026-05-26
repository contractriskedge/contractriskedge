import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/components/auth/AuthProvider";
import { ToastProvider, Toaster } from "@/components/ui/toast";
import { ThemeProvider } from "@/components/theme/ThemeProvider";
import { QueryProvider } from "@/components/QueryProvider";
import { ErrorBoundary } from "@/components/ErrorBoundary";

export const metadata: Metadata = {
  title: "AI Contract Risk Analyzer",
  description: "Enterprise-grade AI-powered contract risk analysis, redlining, and compliance benchmarking platform.",
  keywords: ["contract", "risk", "AI", "legal", "compliance", "redlining"],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full" suppressHydrationWarning>
      <body className="h-full bg-white dark:bg-navy-900 text-navy-900 dark:text-white transition-colors duration-200">
        <ErrorBoundary>
          <QueryProvider>
            <ThemeProvider>
              <AuthProvider>
                <ToastProvider>
                  {children}
                  <Toaster />
                </ToastProvider>
              </AuthProvider>
            </ThemeProvider>
          </QueryProvider>
        </ErrorBoundary>
      </body>
    </html>
  );
}
