/**
 * Template Detail route — view template details, versions, and usage.
 */

"use client";

import React from "react";
import { useParams } from "next/navigation";
import TemplateDetailPage from "@/components/dashboard/templates/TemplateDetailPage";

export default function TemplateDetailRoute() {
  const params = useParams();
  return <TemplateDetailPage templateId={params.templateId as string} />;
}
