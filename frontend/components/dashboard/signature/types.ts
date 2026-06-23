// ── E-Signature Types ───────────────────────────────────────────

export type SignatureProvider = "docusign" | "adobe_sign" | "dropbox_sign";
export type SignatureStatus = "draft" | "sent" | "viewed" | "signed" | "completed" | "declined" | "expired" | "voided";
export type SignerRole = "signer" | "approver" | "cc";
export type SignerStatus = "awaiting" | "sent" | "viewed" | "signed" | "declined";

export interface Signer {
  id: string;
  email: string;
  name: string;
  role: SignerRole;
  signingOrder: number;
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
  providerEnvelopeId?: string;
  expiresAt?: string;
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
  signers: { email: string; name: string; role?: SignerRole; signingOrder?: number }[];
  expiresInDays?: number;
  emailSubject?: string;
  emailBody?: string;
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
  adobe_sign: "Adobe Sign",
  dropbox_sign: "Dropbox Sign",
};

export const STATUS_LABELS: Record<SignatureStatus, string> = {
  draft: "Draft",
  sent: "Sent",
  viewed: "Viewed",
  signed: "Signed",
  completed: "Completed",
  declined: "Declined",
  expired: "Expired",
  voided: "Voided",
};

export const STATUS_COLORS: Record<SignatureStatus, string> = {
  draft: "bg-gray-100 text-gray-600",
  sent: "bg-blue-100 text-blue-700",
  viewed: "bg-amber-100 text-amber-700",
  signed: "bg-green-100 text-green-700",
  completed: "bg-emerald-100 text-emerald-700",
  declined: "bg-red-100 text-red-700",
  expired: "bg-red-100 text-red-700",
  voided: "bg-gray-100 text-gray-500",
};
