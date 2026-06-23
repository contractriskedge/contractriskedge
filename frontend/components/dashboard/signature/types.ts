// ── E-Signature Types ───────────────────────────────────────────

export type SignatureProvider = "docusign";  // adobe_sign, dropbox_sign in Phase 2/3
export type SignatureStatus =
  | "draft" | "preparing" | "sent" | "viewed"
  | "partially_signed" | "completed"
  | "declined" | "expired" | "voided";
export type SignerRole = "signer" | "approver" | "cc" | "carbon_copy";
export type SignerStatus = "awaiting" | "sent" | "viewed" | "signed" | "declined";
export type AuthType = "none" | "email" | "access_code" | "phone" | "kba" | "sms";

export interface Signer {
  id: string;
  email: string;
  name: string;
  title?: string;
  company?: string;
  role: SignerRole;
  signingOrder: number;
  routingOrder: number;
  authenticationType: AuthType;
  phone?: string;
  status: SignerStatus;
  signedAt?: string;
  createdAt: string;
}

export interface SignatureRequest {
  id: string;
  contractId?: string;
  sessionId?: string;
  title: string;
  status: SignatureStatus;
  provider: SignatureProvider;
  providerReference?: string;
  providerMetadata?: Record<string, unknown>;
  emailSubject?: string;
  emailMessage?: string;
  expiresAt?: string;
  reminderDays: number;
  allowDecline: boolean;
  allowPrint: boolean;
  requireIdentityVerification: boolean;
  timezone: string;
  language: string;
  sentAt?: string;
  completedAt?: string;
  createdBy: string;
  createdAt: string;
  updatedAt: string;
  signers: Signer[];
}

export interface SignatureRequestCreate {
  contractId?: string;
  sessionId?: string;
  title: string;
  provider: SignatureProvider;
  signers: {
    email: string;
    name: string;
    title?: string;
    company?: string;
    role?: SignerRole;
    signingOrder?: number;
    routingOrder?: number;
    authenticationType?: AuthType;
    phone?: string;
    accessCode?: string;
  }[];
  emailSubject?: string;
  emailMessage?: string;
  expiresInDays?: number;
  reminderDays?: number;
  allowDecline?: boolean;
  allowPrint?: boolean;
  requireIdentityVerification?: boolean;
  timezone?: string;
  language?: string;
}

export interface AuditEvent {
  id: string;
  eventType: string;
  actorEmail?: string;
  details?: Record<string, unknown>;
  ipAddress?: string;
  createdAt: string;
}

export const PROVIDER_LABELS: Record<SignatureProvider, string> = {
  docusign: "DocuSign",
};

export const STATUS_LABELS: Record<SignatureStatus, string> = {
  draft: "Draft",
  preparing: "Preparing",
  sent: "Sent for Signature",
  viewed: "Viewed",
  partially_signed: "Partially Signed",
  completed: "Completed",
  declined: "Declined",
  expired: "Expired",
  voided: "Voided",
};

export const STATUS_COLORS: Record<SignatureStatus, string> = {
  draft: "bg-gray-100 text-gray-600",
  preparing: "bg-amber-100 text-amber-700",
  sent: "bg-blue-100 text-blue-700",
  viewed: "bg-amber-100 text-amber-700",
  partially_signed: "bg-purple-100 text-purple-700",
  completed: "bg-emerald-100 text-emerald-700",
  declined: "bg-red-100 text-red-700",
  expired: "bg-red-100 text-red-700",
  voided: "bg-gray-100 text-gray-500",
};
