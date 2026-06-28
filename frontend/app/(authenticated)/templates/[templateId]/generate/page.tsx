/**
 * Generate Contract from Template route — wizard for contract generation.
 */

"use client";

import React from "react";
import { useParams } from "next/navigation";
import GenerateContractWizard from "@/components/dashboard/templates/GenerateContractWizard";

export default function GenerateContractPage() {
  const params = useParams();
  const templateId = params?.templateId as string | undefined;
  return <GenerateContractWizard preSelectedTemplateId={templateId} />;
}
