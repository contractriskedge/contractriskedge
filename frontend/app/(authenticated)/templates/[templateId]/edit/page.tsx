/**
 * Edit Template route — edit an existing template.
 */

"use client";

import React from "react";
import { useParams } from "next/navigation";
import TemplateEditorPage from "@/components/dashboard/templates/TemplateEditorPage";

export default function EditTemplatePage() {
  const params = useParams();
  return <TemplateEditorPage templateId={params.templateId as string} />;
}
