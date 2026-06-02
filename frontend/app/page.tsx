"use client";

import React, { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth/AuthProvider";
import { LoginPage } from "@/components/auth/LoginPage";
import { Loader2 } from "lucide-react";

export default function Home() {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && user) {
      router.replace("/dashboard");
    }
  }, [isLoading, user, router]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-navy-900 flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-gold-400 animate-spin" />
      </div>
    );
  }

  if (!user) {
    return <LoginPage />;
  }

  return (
    <div className="min-h-screen bg-navy-900 flex items-center justify-center">
      <Loader2 className="w-8 h-8 text-gold-400 animate-spin" />
    </div>
  );
}
