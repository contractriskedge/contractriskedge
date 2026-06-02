/**
 * Login page — redirects to Auth0 hosted login or shows client-side login.
 */

"use client";

import React, { Suspense, useEffect } from "react";
import { useAuth } from "@/components/auth/AuthProvider";
import { LoginPage as LoginComponent } from "@/components/auth/LoginPage";
import { Loader2 } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";

function LoginPageContent() {
  const { user, isLoading } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const returnTo = searchParams.get("returnTo") || "/dashboard";

  useEffect(() => {
    if (!isLoading && user) {
      router.replace(returnTo);
    }
  }, [isLoading, user, router, returnTo]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-navy-900 flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-gold-400 animate-spin" />
      </div>
    );
  }

  if (user) {
    return (
      <div className="min-h-screen bg-navy-900 flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-gold-400 animate-spin" />
      </div>
    );
  }

  return <LoginComponent />;
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-navy-900 flex items-center justify-center">
          <Loader2 className="w-8 h-8 text-gold-400 animate-spin" />
        </div>
      }
    >
      <LoginPageContent />
    </Suspense>
  );
}
