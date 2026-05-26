const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, HeadingLevel, BorderStyle, WidthType,
  ShadingType, VerticalAlign, PageNumber, PageBreak, LevelFormat,
  TabStopType, TabStopPosition
} = require('docx');
const fs = require('fs');

// Color palette
const C = {
  navy:    '1B3A6B',
  gold:    'C9A84C',
  blue:    '2563EB',
  teal:    '0F766E',
  red:     'DC2626',
  orange:  'EA580C',
  green:   '16A34A',
  gray:    'F3F4F6',
  midgray: '6B7280',
  dark:    '111827',
  white:   'FFFFFF',
  lightblue: 'DBEAFE',
  lightgold: 'FEF3C7',
  lightgreen:'DCFCE7',
  lightorange:'FFF7ED',
};

const border = (color='CCCCCC') => ({ style: BorderStyle.SINGLE, size: 1, color });
const borders = (color='CCCCCC') => ({ top: border(color), bottom: border(color), left: border(color), right: border(color) });

function h1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 360, after: 120 },
    children: [new TextRun({ text, bold: true, size: 36, color: C.navy, font: 'Arial' })]
  });
}
function h2(text, color=C.navy) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 280, after: 100 },
    children: [new TextRun({ text, bold: true, size: 28, color, font: 'Arial' })]
  });
}
function h3(text, color=C.teal) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_3,
    spacing: { before: 200, after: 80 },
    children: [new TextRun({ text, bold: true, size: 24, color, font: 'Arial' })]
  });
}
function para(text, opts={}) {
  return new Paragraph({
    spacing: { before: 80, after: 80 },
    children: [new TextRun({ text, size: 22, font: 'Arial', color: C.dark, ...opts })]
  });
}
function bullet(text, level=0) {
  return new Paragraph({
    numbering: { reference: 'bullets', level },
    spacing: { before: 40, after: 40 },
    children: [new TextRun({ text, size: 22, font: 'Arial', color: C.dark })]
  });
}
function numbered(text, level=0) {
  return new Paragraph({
    numbering: { reference: 'numbers', level },
    spacing: { before: 40, after: 40 },
    children: [new TextRun({ text, size: 22, font: 'Arial', color: C.dark })]
  });
}
function gap() {
  return new Paragraph({ spacing: { before: 60, after: 60 }, children: [new TextRun('')] });
}
function divider(color=C.gold) {
  return new Paragraph({
    spacing: { before: 120, after: 120 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 4, color, space: 1 } },
    children: [new TextRun('')]
  });
}

function cell(text, opts={}) {
  const {
    fill=C.white, bold=false, color=C.dark, colspan=1, w=2340, size=20,
    vAlign=VerticalAlign.CENTER, align=AlignmentType.LEFT
  } = opts;
  return new TableCell({
    columnSpan: colspan,
    verticalAlign: vAlign,
    borders: borders('DDDDDD'),
    width: { size: w, type: WidthType.DXA },
    shading: { fill, type: ShadingType.CLEAR },
    margins: { top: 80, bottom: 80, left: 140, right: 140 },
    children: [new Paragraph({
      alignment: align,
      spacing: { before: 0, after: 0 },
      children: [new TextRun({ text, bold, size, font: 'Arial', color })]
    })]
  });
}

function headerRow(cols, widths, fill=C.navy) {
  return new TableRow({
    tableHeader: true,
    children: cols.map((c, i) => cell(c, { fill, bold: true, color: C.white, w: widths[i], size: 20 }))
  });
}

function dataRow(cols, widths, fills) {
  return new TableRow({
    children: cols.map((c, i) => cell(c, { fill: fills ? fills[i] : C.white, w: widths[i] }))
  });
}

// ─── Cover Page ───────────────────────────────────────────────────────────────
function coverPage() {
  return [
    new Paragraph({ spacing: { before: 1800, after: 0 }, children: [] }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 0, after: 120 },
      children: [new TextRun({ text: '\u2696', size: 96, font: 'Arial' })]
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 0, after: 60 },
      children: [new TextRun({ text: 'AI CONTRACT RISK ANALYZER', bold: true, size: 56, color: C.navy, font: 'Arial' })]
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 0, after: 80 },
      children: [new TextRun({ text: '2026 Gold Standard Enterprise Specification', bold: true, size: 32, color: C.gold, font: 'Arial' })]
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 0, after: 60 },
      border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: C.gold, space: 1 } },
      children: [new TextRun('')]
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 120, after: 40 },
      children: [new TextRun({ text: 'Comprehensive Product Requirements \u2022 Competitive Analysis \u2022 Sprint Roadmap', size: 22, color: C.midgray, font: 'Arial', italics: true })]
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 40, after: 40 },
      children: [new TextRun({ text: 'Target Markets: Legal Ops \u2022 Procurement \u2022 CFO Office \u2022 Mid-Market Law Firms', size: 22, color: C.midgray, font: 'Arial' })]
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 200, after: 40 },
      children: [new TextRun({ text: 'Monetization: $500\u2013$5,000/month per client  |  Version 1.0  |  May 2026', size: 20, color: C.navy, font: 'Arial', bold: true })]
    }),
    new Paragraph({ children: [new PageBreak()] })
  ];
}

// ─── Competitor Table ──────────────────────────────────────────────────────────
function competitorTable() {
  const cols = ['Platform', 'Founded', 'Pricing', 'Core Strength', 'Key Gap', 'Our Advantage'];
  const ws   = [1800, 900, 1400, 2100, 2100, 1800];
  const rows = [
    ['Ironclad CLM', '2017', 'Enterprise $50K+/yr', 'Workflow automation & contract lifecycle management', 'Weak AI risk flagging; no real-time redlining intelligence', 'Deep risk scoring + redline AI at 1/10th the price'],
    ['Kira Systems', '2011', '$30K\u2013$100K/yr', 'ML clause extraction; M&A due diligence', 'No proactive risk benchmarking; legacy UX; slow ingestion', 'RAG-powered benchmarking + modern UX + sub-30s processing'],
    ['Luminance', '2016', '$25K\u2013$80K/yr', 'Legal AI for law firms; multilingual', 'Limited procurement/CFO workflows; no custom risk rubrics', 'Configurable risk rubrics per buyer persona (legal/CFO/proc.)'],
    ['Spellbook (Rally)', '2022', '$99\u2013$499/mo', 'GPT-4 redlines in Word; fast MVP', 'No enterprise ingestion, no RAG, no audit trail, shallow risk', 'Enterprise-grade audit trail + deep RAG + batch processing'],
    ['Harvey AI', '2022', 'Enterprise only', 'LLM legal research & drafting at law firms', 'No CLM, no contract risk scoring, no procurement angle', 'Full risk spectrum + SMB/mid-market price point'],
    ['Evisort', '2016', '$20K\u2013$60K/yr', 'AI metadata extraction + repository', 'Risk scoring is rule-based, not LLM-powered; poor redlining', 'LLM + RAG risk engine vs. rule-based; real redline suggestions'],
    ['LexCheck', '2018', '$15K\u2013$40K/yr', 'Playbook-based redlining for enterprise', 'Static playbooks; no market benchmarking; no RAG learning', 'Dynamic market benchmarks updated quarterly via RAG'],
    ['DocuSign CLM', '2012', '$25K\u2013$75K/yr', 'E-sign + CLM; massive distribution', 'AI is bolted-on; no deep risk analysis; commodity product', 'AI-first architecture; risk is the core, not an afterthought'],
    ['Icertis', '2009', 'Enterprise $100K+', 'Complex enterprise CLM; compliance', 'Extremely expensive; 6-12 month implementation; overkill for MM', 'Land mid-market in days, not months; transparent pricing'],
  ];
  return new Table({
    width: { size: 9900, type: WidthType.DXA },
    columnWidths: ws,
    rows: [
      headerRow(cols, ws),
      ...rows.map((r, i) => new TableRow({
        children: r.map((c, j) => cell(c, {
          fill: i % 2 === 0 ? C.gray : C.white,
          w: ws[j],
          size: 18,
          color: j === 5 ? C.teal : C.dark,
          bold: j === 5
        }))
      }))
    ]
  });
}

// ─── Capability Matrix ─────────────────────────────────────────────────────────
function capabilityMatrix() {
  const cols = ['Capability', 'Priority', 'Competitor Coverage', 'Market Gap', 'Our Approach'];
  const ws   = [2600, 900, 2000, 1700, 2700];
  const rows = [
    ['PDF/DOCX Ingestion (<30s)', 'Must', 'All cover basic', 'None handle 500pg+ well', 'Async chunked ingestion + OCR fallback for scanned docs'],
    ['LLM Risk Clause Flagging', 'Must', 'Kira, Evisort (rule-based)', 'No LLM-native real-time flagging', 'Claude/GPT-4 with legal-fine-tuned risk taxonomy'],
    ['AI Redline Suggestions', 'Must', 'Spellbook, LexCheck', 'Limited to playbooks; no reasoning', 'Contextual redlines with plain-English rationale'],
    ['Market Benchmark Scoring', 'Must', 'None fully implement', 'Critical gap \u2014 all lack live benchmarks', 'Quarterly-updated RAG corpus of 10K+ market contracts'],
    ['Risk Dashboard & Heatmap', 'Must', 'Partial (Ironclad)', 'CFO-facing view missing everywhere', 'Role-specific views: Legal / Procurement / CFO'],
    ['Clause-Level Audit Trail', 'Must', 'Ironclad, Icertis', 'SMB/MM tools lack this entirely', 'Immutable audit log with diff viewer'],
    ['Multi-Format Export', 'Must', 'Most support DOCX/PDF', 'JSON/API output missing for procurement', 'DOCX tracked-changes + PDF + JSON API output'],
    ['Role-Based Access Control', 'Must', 'Enterprise tools only', 'SMB tools have none', 'Team/Org/Admin hierarchy with clause-level permissions'],
    ['Playbook Configuration', 'Should', 'LexCheck, Ironclad', 'Not editable by non-lawyers', 'No-code playbook builder for legal ops'],
    ['Multi-Language Support', 'Should', 'Luminance', 'English-only tools miss global deals', 'EN/ES/FR/DE/ZH at launch; 20+ by v2'],
    ['CRM/ERP Integrations', 'Should', 'Icertis, Ironclad', 'Salesforce integration always half-baked', 'Native SF/HubSpot/SAP connectors + Zapier'],
    ['Counterparty Risk Scoring', 'Should', 'None', 'Completely unaddressed in market', 'D&B/Creditsafe API + public litigation scrape'],
    ['Real-Time Collaboration', 'Should', 'Ironclad, DocuSign', 'No in-line commenting like Google Docs', 'Google Docs-style co-editing with AI suggestions inline'],
    ['Contract Comparison (v2v)', 'Should', 'Kira (M&A only)', 'Version diff is manual everywhere', 'Semantic diff across unlimited versions with change timeline'],
    ['API-First Architecture', 'Should', 'Harvey, Evisort', 'Webhook/event system missing widely', 'REST + GraphQL + webhook event bus'],
    ['White-Label OEM Mode', 'Nice', 'None', 'Law firms want to brand the tool', 'Full white-label with custom domain + logo + color scheme'],
    ['AI Negotiation Coach', 'Nice', 'None', 'No tool trains negotiators in real-time', 'Simulated negotiation sandbox with AI opposing counsel'],
    ['Predictive Dispute Risk', 'Nice', 'None', 'Courts data never incorporated', 'PACER + litigation history \u2192 dispute probability model'],
    ['Voice/Email Intake', 'Nice', 'None', 'Contracts still sent as email attachments', 'Gmail/Outlook plugin auto-ingests + flags on receipt'],
    ['ESG Clause Analysis', 'Nice', 'None', 'Zero tools cover ESG/sustainability risk', 'ESG risk rubric: supplier ethics, carbon commitments, DEI'],
  ];
  const pColors = { 'Must': C.lightgold, 'Should': C.lightblue, 'Nice': C.lightgreen };
  const pText   = { 'Must': C.orange, 'Should': C.blue, 'Nice': C.green };
  return new Table({
    width: { size: 9900, type: WidthType.DXA },
    columnWidths: ws,
    rows: [
      headerRow(cols, ws),
      ...rows.map((r, i) => new TableRow({
        children: r.map((c, j) => {
          const p = r[1];
          return cell(c, {
            fill: j === 1 ? pColors[p] : (i % 2 === 0 ? C.gray : C.white),
            w: ws[j], size: 18,
            color: j === 1 ? pText[p] : C.dark,
            bold: j === 0 || j === 1
          });
        })
      }))
    ]
  });
}

// ─── Use Cases Table ───────────────────────────────────────────────────────────
function useCasesTable() {
  const cols = ['#', 'Use Case', 'Persona', 'User Story', 'Acceptance Criteria', 'Priority'];
  const ws   = [400, 1600, 900, 2400, 2800, 800];
  const rows = [
    ['UC-01', 'Contract Ingestion', 'Legal Ops', 'As a legal ops manager, I upload a 200-page MSA PDF and receive a risk report in under 60 seconds', '95% clause extraction accuracy; handles scanned PDFs; supports DOCX, PDF, TXT', 'Must'],
    ['UC-02', 'Risk Clause Flagging', 'Legal Counsel', 'As counsel, I see every high-risk clause highlighted with severity scores and reasoning so I can prioritize review', 'Risk flagged with: severity (1-10), clause type, page ref, rationale; <5% false positive rate', 'Must'],
    ['UC-03', 'AI Redline Suggestions', 'Legal Ops', 'As a legal ops lead, I receive specific replacement language for each flagged clause with plain-English explanation', 'Suggested redline with original vs. proposed text; rationale; accepts/rejects tracked in audit log', 'Must'],
    ['UC-04', 'Market Benchmark Report', 'CFO / Legal', 'As CFO, I see how our contract terms compare to market standards so I know where we are over- or under-exposed', 'Score vs. market median/P25/P75 for 12+ clause types; updated quarterly; source citation included', 'Must'],
    ['UC-05', 'Risk Dashboard', 'CFO', 'As CFO, I have a one-page portfolio view of all active contracts showing aggregate risk exposure and trending', 'Heatmap of contracts by risk; total $ exposure at risk; drill-down to clause level; exportable', 'Must'],
    ['UC-06', 'Playbook Configuration', 'Legal Ops', 'As a legal ops manager, I configure company-specific risk rules without writing code or involving IT', 'No-code playbook builder; test mode; version history; role-based deployment', 'Must'],
    ['UC-07', 'Batch Processing', 'Procurement', 'As a procurement director, I upload 50 vendor contracts simultaneously and receive a comparative risk matrix', 'Parallel ingestion; comparison matrix exported to Excel; completion within 10 min for 50 contracts', 'Must'],
    ['UC-08', 'Audit Trail & Compliance', 'Legal Ops', 'As legal ops, I produce a full audit log of all AI recommendations, user actions, and approvals for regulatory review', 'Tamper-evident log; exportable PDF/CSV; GDPR/SOC2 compliant; 7-year retention option', 'Must'],
    ['UC-09', 'Counterparty Risk Profile', 'Procurement', 'As a procurement manager, I see a counterparty\'s financial health and litigation history before signing', 'D&B score + litigation count + news sentiment; updated at contract creation; risk flag threshold', 'Should'],
    ['UC-10', 'Multi-Language Analysis', 'Legal (Global)', 'As a global legal team, I analyze contracts in Spanish, French, German, and Chinese with the same accuracy as English', 'EN/ES/FR/DE/ZH at launch; accuracy parity \u226590% vs. English baseline; language auto-detected', 'Should'],
    ['UC-11', 'CRM Integration', 'Sales / Legal', 'As a sales leader, contract risk data flows into Salesforce opportunity records without manual copying', 'Bidirectional SF sync; risk score field auto-populated; contract stage updates triggered by AI flags', 'Should'],
    ['UC-12', 'Version Comparison', 'Legal Counsel', 'As counsel in negotiation, I see a semantic diff between our v1 and counterparty\'s redlined v2 instantly', 'Side-by-side view; semantic (not just text) diff; added/removed/modified clause categorization', 'Should'],
    ['UC-13', 'Email/Gmail Ingestion', 'Legal / Proc.', 'As a user, contracts emailed to me are auto-detected, ingested, and flagged without any manual upload step', 'Gmail/Outlook plugin; auto-ingestion trigger; user notification with risk summary; opt-out control', 'Nice'],
    ['UC-14', 'Negotiation Sandbox', 'Legal Counsel', 'As a junior lawyer, I practice negotiating an NDA against an AI opposing counsel to build my skills', 'Simulated negotiation with AI opponent; coach mode with hints; session scoring; export practice log', 'Nice'],
    ['UC-15', 'ESG Risk Analysis', 'Procurement / ESG', 'As an ESG officer, I flag contracts missing supplier sustainability commitments or DEI clauses', 'ESG rubric covering: emissions, labor, ethics, DEI; gap report vs. company ESG policy', 'Nice'],
  ];
  const pColors = { 'Must': C.lightgold, 'Should': C.lightblue, 'Nice': C.lightgreen };
  const pText   = { 'Must': C.orange, 'Should': C.blue, 'Nice': C.green };
  return new Table({
    width: { size: 9900, type: WidthType.DXA },
    columnWidths: ws,
    rows: [
      headerRow(cols, ws),
      ...rows.map((r, i) => new TableRow({
        children: r.map((c, j) => {
          const p = r[5];
          return cell(c, {
            fill: j === 5 ? pColors[p] : (i % 2 === 0 ? C.gray : C.white),
            w: ws[j], size: 17,
            color: j === 5 ? pText[p] : (j === 0 ? C.navy : C.dark),
            bold: j === 0 || j === 5
          });
        })
      }))
    ]
  });
}

// ─── Tech Architecture Table ───────────────────────────────────────────────────
function techTable() {
  const cols = ['Layer', 'Component', 'Technology Choice', 'Rationale'];
  const ws   = [1600, 2000, 2200, 4100];
  const rows = [
    ['Ingestion', 'Document Parser', 'Apache Tika + PyMuPDF + AWS Textract (OCR)', 'Handles PDF/DOCX/scanned; 99%+ extraction accuracy; async queue'],
    ['Ingestion', 'Chunking Strategy', 'Semantic clause chunker (custom NLP)', 'Clause-aware splits preserve legal meaning; 512-token max chunks'],
    ['AI Core', 'Primary LLM', 'Claude 3.5 Sonnet / GPT-4o (switchable)', 'Legal reasoning quality; cost per token balanced; provider redundancy'],
    ['AI Core', 'RAG Pipeline', 'LlamaIndex + Pinecone vector DB', 'Sub-100ms retrieval; 10M+ clause corpus; namespace isolation per tenant'],
    ['AI Core', 'Fine-tuning Layer', 'LoRA adapters on legal dataset (CUAD + custom)', 'Domain accuracy boost; ~40% fewer hallucinations vs. zero-shot'],
    ['Backend', 'API Layer', 'FastAPI (Python) + Node.js BFF', 'FastAPI for AI workloads; Node BFF for real-time WebSocket features'],
    ['Backend', 'Job Queue', 'Redis + Celery (async processing)', 'Handles burst ingestion; retry logic; job status webhooks'],
    ['Backend', 'Database', 'PostgreSQL + pgvector + Redis cache', 'Relational integrity + native vector search + hot data caching'],
    ['Frontend', 'Web App', 'Next.js 14 + TypeScript + Tailwind', 'SSR for SEO/perf; type safety; rapid UI iteration'],
    ['Frontend', 'Document Editor', 'ProseMirror + custom diff renderer', 'Legal-grade tracked-changes; clause-level commenting; real-time collab'],
    ['Security', 'Auth & AuthZ', 'Auth0 + RBAC + attribute-based access', 'SOC2 T2 compliant; SCIM provisioning; clause-level permission model'],
    ['Security', 'Data Encryption', 'AES-256 at rest; TLS 1.3 in transit', 'GDPR/HIPAA/CCPA alignment; tenant key isolation; HSM key management'],
    ['Infra', 'Cloud', 'AWS (primary) + multi-region active-passive', '99.95% SLA; data residency options (EU/US/APAC); SOC2 certified'],
    ['Integrations', 'Connectors', 'Salesforce + HubSpot + SAP + Zapier + REST API', 'Native integrations avoid middleware complexity; webhook event bus'],
    ['Observability', 'Monitoring', 'Datadog + Sentry + custom LLM eval pipeline', 'Real-time hallucination detection; accuracy regression alerts; cost tracking'],
  ];
  return new Table({
    width: { size: 9900, type: WidthType.DXA },
    columnWidths: ws,
    rows: [
      headerRow(cols, ws),
      ...rows.map((r, i) => new TableRow({
        children: r.map((c, j) => cell(c, {
          fill: i % 2 === 0 ? C.gray : C.white,
          w: ws[j], size: 18,
          color: j === 0 ? C.navy : (j === 2 ? C.teal : C.dark),
          bold: j === 0
        }))
      }))
    ]
  });
}

// ─── Pricing Table ─────────────────────────────────────────────────────────────
function pricingTable() {
  const cols = ['Tier', 'Price/Month', 'Target', 'Contracts/Month', 'Users', 'Key Features'];
  const ws   = [1400, 1200, 1600, 1400, 800, 3500];
  const rows = [
    ['Starter', '$500', 'Solo attorneys, small firms', '20', '3', 'PDF/DOCX ingestion, risk flagging, 5 redline types, email support'],
    ['Growth', '$1,500', 'Mid-market law firms, legal ops teams', '100', '15', 'All Starter + market benchmarking, playbook builder, CRM integration, priority support'],
    ['Professional', '$3,500', 'Procurement teams, multi-practice firms', '500', '50', 'All Growth + batch processing, counterparty risk, multi-language, white-glove onboarding'],
    ['Enterprise', '$5,000+', 'Large enterprises, CFO offices, Fortune 1000', 'Unlimited', 'Unlimited', 'All Pro + white-label, SSO/SCIM, custom RAG corpus, dedicated CSM, SLA 99.95%'],
    ['Law Firm OEM', 'Custom', 'Law firms reselling to clients', 'Custom', 'Custom', 'White-label, revenue share model, branded portal, co-marketing support'],
  ];
  const fills = [C.lightgreen, C.lightblue, C.lightgold, C.lightorange, C.gray];
  const textc = [C.green, C.blue, C.orange, C.red, C.midgray];
  return new Table({
    width: { size: 9900, type: WidthType.DXA },
    columnWidths: ws,
    rows: [
      headerRow(cols, ws),
      ...rows.map((r, i) => new TableRow({
        children: r.map((c, j) => cell(c, {
          fill: j === 0 ? fills[i] : C.white,
          w: ws[j], size: 18,
          color: j === 0 ? textc[i] : (j === 1 ? C.green : C.dark),
          bold: j === 0 || j === 1
        }))
      }))
    ]
  });
}

// ─── Risk Taxonomy Table ───────────────────────────────────────────────────────
function riskTaxTable() {
  const cols = ['Risk Category', 'Clause Types Covered', 'Severity Default', 'Auto-Redline', 'Benchmark Data'];
  const ws   = [1800, 3000, 1400, 1200, 2500];
  const rows = [
    ['Liability Exposure', 'Limitation of liability, indemnification, liquidated damages, consequential damages caps', 'High (8-10)', 'Yes', 'P25/P50/P75 caps by deal size & industry'],
    ['Termination Rights', 'T-for-convenience, T-for-cause, notice periods, cure periods, auto-renewal traps', 'High (7-9)', 'Yes', 'Notice period norms by contract type'],
    ['IP & Data Ownership', 'Work-for-hire, IP assignment, data license, residual rights, background IP', 'High (8-10)', 'Yes', 'Market standards by industry vertical'],
    ['Payment & Financial', 'Payment terms, late fees, price escalation, audit rights, currency risk', 'Medium (5-7)', 'Yes', 'Net-30/60/90 distribution by segment'],
    ['Governing Law', 'Jurisdiction, choice of law, venue, arbitration vs. litigation, class action waiver', 'Medium (5-8)', 'Partial', 'Preferred jurisdictions by counterparty HQ'],
    ['Confidentiality', 'NDA scope, duration, carve-outs, return of information, survival clauses', 'Medium (4-7)', 'Yes', 'Standard NDA term lengths by industry'],
    ['Force Majeure', 'Scope definition, notice requirements, supply chain events, pandemic clauses', 'Medium (5-7)', 'Yes', 'Post-COVID market language benchmarks'],
    ['Compliance & Regulatory', 'GDPR/CCPA data processing, AML, sanctions, export controls, SOX compliance', 'High (7-10)', 'Partial', 'Regulatory requirement flags by geography'],
    ['Change of Control', 'Assignment restrictions, CoC triggers, step-in rights, consent requirements', 'Medium (5-8)', 'Yes', 'Market-standard CoC protections'],
    ['SLA & Performance', 'Uptime SLAs, remedies, credits, measurement methodology, exclusions', 'Low-Med (3-6)', 'Yes', 'Industry SLA benchmarks by service type'],
    ['Non-Compete / Exclusivity', 'Non-solicitation, geographic scope, duration, market exclusivity', 'High (7-9)', 'Yes', 'Enforceability norms by state/country'],
    ['ESG / Sustainability', 'Carbon commitments, supplier ethics, DEI requirements, modern slavery', 'Low (1-4)', 'No', 'Emerging ESG clause database (growing)'],
  ];
  const sColors = { 'High': C.lightorange, 'Medium': C.lightblue, 'Low': C.lightgreen, 'Low-Med': C.lightgreen };
  return new Table({
    width: { size: 9900, type: WidthType.DXA },
    columnWidths: ws,
    rows: [
      headerRow(cols, ws),
      ...rows.map((r, i) => {
        const sev = r[2].split(' ')[0];
        return new TableRow({
          children: r.map((c, j) => cell(c, {
            fill: j === 2 ? (sColors[sev] || C.gray) : (i % 2 === 0 ? C.gray : C.white),
            w: ws[j], size: 18,
            color: j === 0 ? C.navy : (j === 2 ? C.orange : C.dark),
            bold: j === 0 || j === 2
          }))
        });
      })
    ]
  });
}

// ─── KPI Table ─────────────────────────────────────────────────────────────────
function kpiTable() {
  const cols = ['KPI', 'Target (Year 1)', 'Target (Year 2)', 'Measurement Method'];
  const ws   = [2500, 1800, 1800, 3800];
  const rows = [
    ['Clause Extraction Accuracy', '\u226595%', '\u226598%', 'Sampled weekly vs. human expert review (500 clause blind test)'],
    ['Risk Flag False Positive Rate', '<5%', '<2%', 'User feedback loop + monthly attorney audit'],
    ['Contract Processing Time', '<60 sec (20pg)', '<30 sec (20pg)', 'P95 latency tracked in Datadog; alert if >90s'],
    ['Redline Acceptance Rate', '>40%', '>60%', 'Tracked in audit log; segment by clause type & industry'],
    ['Market Benchmark Freshness', 'Quarterly update', 'Monthly update', 'RAG corpus update timestamp; data staleness alert if >90 days'],
    ['System Uptime (Enterprise)', '99.9%', '99.95%', 'Synthetic monitoring + StatusPage public dashboard'],
    ['API Response Time (P95)', '<500ms', '<200ms', 'Datadog APM; SLA breach alerting'],
    ['Customer Satisfaction (NPS)', '>50', '>65', 'In-app survey at 30/90/180-day marks'],
    ['Time-to-Value (Onboarding)', '<2 hours', '<30 min', 'Time from signup to first risk report; tracked in product analytics'],
    ['ARR Growth', '$2M', '$8M', 'Stripe + CRM tracked; monthly board reporting'],
  ];
  return new Table({
    width: { size: 9900, type: WidthType.DXA },
    columnWidths: ws,
    rows: [
      headerRow(cols, ws),
      ...rows.map((r, i) => new TableRow({
        children: r.map((c, j) => cell(c, {
          fill: i % 2 === 0 ? C.gray : C.white,
          w: ws[j], size: 18,
          color: j === 1 ? C.green : (j === 2 ? C.teal : C.dark),
          bold: j === 0 || j === 1 || j === 2
        }))
      }))
    ]
  });
}

// ─── Build Document ────────────────────────────────────────────────────────────
const doc = new Document({
  numbering: {
    config: [
      { reference: 'bullets', levels: [
        { level: 0, format: LevelFormat.BULLET, text: '\u2022', alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } },
        { level: 1, format: LevelFormat.BULLET, text: '\u25CB', alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 1080, hanging: 360 } } } },
      ]},
      { reference: 'numbers', levels: [
        { level: 0, format: LevelFormat.DECIMAL, text: '%1.', alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } },
      ]},
    ]
  },
  styles: {
    default: { document: { run: { font: 'Arial', size: 22 } } },
    paragraphStyles: [
      { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 36, bold: true, font: 'Arial', color: C.navy },
        paragraph: { spacing: { before: 360, after: 120 }, outlineLevel: 0 } },
      { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 28, bold: true, font: 'Arial', color: C.navy },
        paragraph: { spacing: { before: 280, after: 100 }, outlineLevel: 1 } },
      { id: 'Heading3', name: 'Heading 3', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 24, bold: true, font: 'Arial', color: C.teal },
        paragraph: { spacing: { before: 200, after: 80 }, outlineLevel: 2 } },
    ]
  },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1440, right: 1080, bottom: 1440, left: 1080 }
      }
    },
    headers: {
      default: new Header({
        children: [
          new Paragraph({
            alignment: AlignmentType.RIGHT,
            border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: C.gold, space: 1 } },
            spacing: { before: 0, after: 100 },
            children: [
              new TextRun({ text: 'AI Contract Risk Analyzer \u2014 2026 Gold Standard Specification  |  CONFIDENTIAL', size: 18, color: C.midgray, font: 'Arial' })
            ]
          })
        ]
      })
    },
    footers: {
      default: new Footer({
        children: [
          new Paragraph({
            alignment: AlignmentType.CENTER,
            border: { top: { style: BorderStyle.SINGLE, size: 4, color: C.gold, space: 1 } },
            spacing: { before: 100, after: 0 },
            children: [
              new TextRun({ text: 'Page ', size: 18, color: C.midgray, font: 'Arial' }),
              new TextRun({ children: [PageNumber.CURRENT], size: 18, color: C.midgray, font: 'Arial' }),
              new TextRun({ text: ' of ', size: 18, color: C.midgray, font: 'Arial' }),
              new TextRun({ children: [PageNumber.TOTAL_PAGES], size: 18, color: C.midgray, font: 'Arial' }),
              new TextRun({ text: '  |  \u00A9 2026 AI Contract Risk Analyzer. All rights reserved.', size: 18, color: C.midgray, font: 'Arial' }),
            ]
          })
        ]
      })
    },
    children: [
      // ── Cover ──────────────────────────────────────────────────────────
      ...coverPage(),

      // ── 1. Executive Summary ───────────────────────────────────────────
      h1('1. Executive Summary'),
      divider(),
      para('The AI Contract Risk Analyzer is a 2026-generation, LLM + RAG-powered platform that ingests legal contracts (PDF/DOCX), automatically flags risk clauses with severity scores, generates AI-drafted redline suggestions, and benchmarks contract terms against a quarterly-updated corpus of 10,000+ market contracts. Designed for legal ops teams, procurement directors, and CFO offices, it delivers enterprise-grade accuracy at mid-market pricing ($500\u2013$5,000/month).'),
      gap(),
      h3('Why Now?'),
      bullet('LLM reasoning quality (Claude 3.5, GPT-4o) now achieves \u226595% clause extraction accuracy \u2014 the accuracy threshold required for legal workflows'),
      bullet('RAG architectures solve the hallucination problem that made earlier AI legal tools commercially unviable'),
      bullet('Legal AI is the #1 VC investment vertical in LegalTech for 2024\u20132026; $2.8B deployed in 18 months'),
      bullet('Post-pandemic contract complexity (force majeure, supply chain, data residency) has outpaced manual review capacity'),
      bullet('Mid-market legal teams (5-50 attorneys) are severely underserved \u2014 enterprise tools cost $50K+/year with 6-month implementations'),
      gap(),
      h3('Strategic Positioning'),
      bullet('Target: Mid-market law firms, legal ops teams at growth-stage companies, and procurement divisions at $100M\u2013$2B revenue companies'),
      bullet('Differentiation: AI-first architecture (risk IS the product, not an add-on); configurable risk rubrics; role-specific dashboards for legal, procurement, and CFO personas'),
      bullet('Moat: Proprietary RAG corpus of anonymized market contract benchmarks; continuously improving LoRA fine-tuned legal model'),
      bullet('Go-to-Market: Product-led growth (free trial \u2192 paid); law firm channel partners; CFO/procurement conference presence'),
      gap(),
      new Paragraph({ children: [new PageBreak()] }),

      // ── 2. Market & Competitor Analysis ───────────────────────────────
      h1('2. Competitive Landscape Analysis'),
      divider(),
      para('Nine major platforms compete in the AI contract analysis space. The table below maps each competitor\'s core strength, critical gap, and our specific advantage. The market is bifurcated: expensive enterprise CLMs ($50K+/yr, 6-month implementations) and lightweight GPT wrappers with shallow risk analysis. Our product owns the underserved middle.'),
      gap(),
      competitorTable(),
      gap(),
      h3('Market Gap Summary'),
      bullet('No platform delivers LLM-native risk flagging + AI redlines + live market benchmarking in a single product at mid-market price points'),
      bullet('CFO-facing risk dashboards are absent across all competitors \u2014 financial exposure views exist only in Excel exports'),
      bullet('Counterparty financial risk integration is completely unaddressed \u2014 every tool analyzes the contract, none analyze the counterparty'),
      bullet('Procurement-specific workflows (vendor onboarding, batch processing, comparative analysis) are afterthoughts in legal-first tools'),
      bullet('ESG clause analysis is a $0 addressable market today \u2014 first-mover advantage for v2 launch in 2027'),
      gap(),
      new Paragraph({ children: [new PageBreak()] }),

      // ── 3. Capability Requirements ─────────────────────────────────────
      h1('3. Capability Requirements (MoSCoW Framework)'),
      divider(),
      para('Requirements are classified using the MoSCoW framework: Must Have (launch blockers), Should Have (v1.1 within 90 days of launch), Nice to Have (v2 roadmap items). The capability matrix below maps each feature to its competitor coverage, market gap, and our implementation approach.'),
      gap(),
      h3('Legend:  Must = Launch Critical    Should = 90-Day Roadmap    Nice = v2 Vision'),
      gap(),
      capabilityMatrix(),
      gap(),
      new Paragraph({ children: [new PageBreak()] }),

      // ── 4. Must Have ──────────────────────────────────────────────────
      h1('4. Must-Have Capabilities (Launch Requirements)'),
      divider(),

      h2('4.1 Contract Ingestion Engine'),
      bullet('Supported formats: PDF (text and scanned/OCR), DOCX, DOC, TXT, RTF'),
      bullet('Processing SLA: < 60 seconds for 50-page contract at P95; < 3 minutes for 200-page contract'),
      bullet('OCR pipeline: AWS Textract as primary; Tesseract as fallback for budget tiers'),
      bullet('Clause segmentation: ML-based clause boundary detection trained on CUAD + proprietary dataset'),
      bullet('Chunking strategy: Semantic clause-aware chunking; 512-token max; overlap-aware for cross-reference preservation'),
      bullet('File size limits: 50MB per file; 500MB per batch upload; configurable per tier'),
      bullet('Ingestion API: REST endpoint for programmatic upload; webhook on completion'),
      gap(),

      h2('4.2 AI Risk Clause Flagging'),
      bullet('Risk taxonomy: 12 primary categories (see Section 7 \u2014 Risk Taxonomy)'),
      bullet('Severity scoring: 1\u201310 scale with confidence interval; calibrated against attorney feedback dataset'),
      bullet('Flagging output: Clause text + page reference + risk category + severity + plain-English rationale + suggested action'),
      bullet('False positive rate: < 5% for standard commercial contracts (NDA, MSA, SOW, SaaS agreements)'),
      bullet('LLM backbone: Claude 3.5 Sonnet (primary); GPT-4o (fallback); switchable per enterprise tenant'),
      bullet('Fine-tuning: LoRA adapters trained on 50,000+ annotated legal clauses; updated quarterly'),
      bullet('Context window: Full contract fed via RAG chunking + summary compression for contracts > 100K tokens'),
      gap(),

      h2('4.3 AI Redline Suggestions'),
      bullet('Output format: Original text vs. proposed replacement with change highlighting (tracked-changes compatible)'),
      bullet('Reasoning: Plain-English explanation for every redline (2\u20134 sentences minimum)'),
      bullet('Redline types covered: Liability caps, indemnification, IP ownership, payment terms, governing law, termination, confidentiality, force majeure'),
      bullet('Acceptance tracking: Accept/reject/modify tracked in audit log with user attribution'),
      bullet('Export: DOCX with native tracked changes; PDF markup; JSON for API consumers'),
      bullet('Redline confidence: Displayed per suggestion; low-confidence suggestions flagged for attorney review'),
      gap(),

      h2('4.4 Market Benchmark Scoring'),
      bullet('Benchmark corpus: 10,000+ anonymized commercial contracts; quarterly refresh; curated by legal AI team'),
      bullet('Benchmark dimensions: Payment terms, liability caps, IP assignment, termination notice, governing law, indemnification scope'),
      bullet('Output: Percentile score (P25/P50/P75) per clause type vs. market; favorable/unfavorable/at-market classification'),
      bullet('Segmentation: Benchmarks segmented by: deal size ($1M, $5M, $10M+), industry (SaaS, Manufacturing, Services, Healthcare), counterparty type (enterprise vs. SMB)'),
      bullet('Freshness indicator: Data age displayed per benchmark; alert if corpus > 90 days old'),
      bullet('Source transparency: Representative anonymized examples available on request; methodology documentation included'),
      gap(),

      h2('4.5 Risk Dashboard & Reporting'),
      bullet('Portfolio view: All active contracts with risk heatmap (RAG \u2014 Red/Amber/Green scoring)'),
      bullet('Financial exposure: Aggregate $ at risk by risk category across all contracts'),
      bullet('Persona views: Legal view (clause detail), Procurement view (vendor risk), CFO view (financial exposure summary)'),
      bullet('Drill-down: Contract \u2192 Section \u2192 Clause \u2192 Flagged Risk \u2192 Redline Suggestion'),
      bullet('Export: PDF executive report; Excel risk register; CSV data export; API JSON'),
      bullet('Scheduling: Automated weekly/monthly risk summary email with configurable recipients'),
      gap(),

      h2('4.6 Role-Based Access Control'),
      bullet('Roles: Super Admin, Org Admin, Legal Reviewer, Procurement Analyst, CFO Viewer, External Counsel (read-only)'),
      bullet('Granularity: Clause-level visibility controls; contract-level access lists; department-level data isolation'),
      bullet('Provisioning: Manual invite + SCIM 2.0 automated provisioning (Enterprise tier)'),
      bullet('SSO: SAML 2.0 + OIDC; Okta, Azure AD, Google Workspace out-of-box (Enterprise tier)'),
      gap(),

      h2('4.7 Audit Trail & Compliance'),
      bullet('Immutable log: All AI recommendations, user actions, approvals, exports; tamper-evident with hash chaining'),
      bullet('Retention: 1-year default; 7-year option (Enterprise); configurable per jurisdiction'),
      bullet('Export: PDF audit report for regulatory submission; CSV for data analysis'),
      bullet('Compliance: SOC 2 Type II; GDPR (data residency options: US, EU, APAC); CCPA; HIPAA-ready (Business Associate Agreement available)'),
      bullet('Encryption: AES-256 at rest; TLS 1.3 in transit; tenant key isolation; HSM key management (Enterprise)'),
      gap(),
      new Paragraph({ children: [new PageBreak()] }),

      // ── 5. Should Have ─────────────────────────────────────────────────
      h1('5. Should-Have Capabilities (90-Day Roadmap)'),
      divider(),

      h2('5.1 Playbook Configuration (No-Code)'),
      para('A no-code playbook builder allows legal ops managers \u2014 not IT or developers \u2014 to define company-specific risk rules, acceptable clause language, and approval thresholds.'),
      bullet('Visual rule builder: IF [clause type] + [condition] THEN [severity] + [suggested language]'),
      bullet('Playbook versioning: Full version history; rollback; approval workflow before activation'),
      bullet('Test mode: Run playbook against historical contracts before deploying to production'),
      bullet('Template library: 20+ pre-built playbooks for common contract types (NDA, MSA, SaaS, Employment)'),
      gap(),

      h2('5.2 Multi-Language Support'),
      bullet('Languages at launch: English, Spanish, French, German, Mandarin Chinese'),
      bullet('Accuracy target: \u2265 90% parity with English baseline across all supported languages'),
      bullet('Auto-detection: Language detected automatically at ingestion; no user configuration required'),
      bullet('Benchmark data: Market benchmarks available for US, UK, EU, and APAC contract markets'),
      gap(),

      h2('5.3 CRM & Procurement System Integrations'),
      bullet('Salesforce: Bidirectional sync; risk score \u2192 Opportunity field; contract stage triggers; AppExchange listing'),
      bullet('HubSpot: Risk score + contract summary pushed to Deal record; native HubSpot app'),
      bullet('SAP Ariba / Coupa: Contract metadata sync for procurement workflows; PO-level risk linkage'),
      bullet('Zapier / Make: 500+ app connections via webhook; no-code automation for non-technical users'),
      bullet('REST API + GraphQL: Full API access for custom integrations; SDK in Python, Node.js, Ruby'),
      gap(),

      h2('5.4 Counterparty Risk Scoring'),
      bullet('Data sources: Dun & Bradstreet financial health score; Creditsafe; public litigation scrape (PACER); news sentiment (Google News API)'),
      bullet('Risk dimensions: Financial stability, litigation history, regulatory violations, news sentiment'),
      bullet('Output: Counterparty risk card alongside contract risk report; combined deal risk score'),
      bullet('Thresholds: Configurable alert thresholds per risk dimension; auto-flag high-risk counterparties'),
      gap(),

      h2('5.5 Real-Time Collaboration'),
      bullet('Co-editing: Google Docs-style concurrent editing with AI suggestions inline'),
      bullet('Comments: Clause-level threaded comments; @mention notifications; resolution tracking'),
      bullet('Activity feed: Real-time feed of collaborator actions within a contract'),
      bullet('Presence indicators: Show who is reviewing which clause in real-time'),
      gap(),

      h2('5.6 Contract Version Comparison'),
      bullet('Semantic diff: Compare any two contract versions; semantic (not just text) change detection'),
      bullet('Clause-level diff: Added, removed, modified clauses categorized; risk delta between versions highlighted'),
      bullet('Timeline view: Full negotiation history with version graph; identify regression risks'),
      bullet('Side-by-side: Split-pane view with synchronized scrolling'),
      gap(),
      new Paragraph({ children: [new PageBreak()] }),

      // ── 6. Nice to Have ────────────────────────────────────────────────
      h1('6. Nice-to-Have Capabilities (v2 Vision)'),
      divider(),

      h2('6.1 White-Label OEM Mode'),
      para('Law firms and procurement consultancies can deploy the platform under their own brand, enabling a reseller channel that dramatically accelerates distribution without direct sales cost.'),
      bullet('Full white-label: Custom domain, logo, color scheme, email branding'),
      bullet('Revenue share: 30/70 split (platform/partner) on client revenues'),
      bullet('Partner portal: Deal registration, co-marketing assets, training certification'),
      gap(),

      h2('6.2 AI Negotiation Coach'),
      para('A simulation environment where attorneys and procurement professionals practice contract negotiation against an AI opposing counsel trained on counterparty archetypes.'),
      bullet('Scenario library: NDA, SaaS MSA, hardware purchase, employment, M&A; configurable counterparty aggressiveness'),
      bullet('Coach mode: Real-time hints; post-session scoring on 12 negotiation dimensions'),
      bullet('Team training: Session replay; manager review; team leaderboard; CPD credits integration'),
      gap(),

      h2('6.3 Predictive Dispute Risk'),
      bullet('Data sources: PACER court records; arbitration outcomes; industry dispute databases'),
      bullet('Model: XGBoost classifier predicting dispute probability within 24 months of signing, by clause type'),
      bullet('Output: Dispute probability score per contract + specific clauses most predictive of disputes'),
      gap(),

      h2('6.4 Email & Gmail/Outlook Auto-Ingestion'),
      bullet('Plugin: Gmail and Outlook plugins auto-detect contract attachments; one-click ingestion'),
      bullet('Auto-analysis: Immediately trigger risk analysis on detected contracts; email summary to sender'),
      bullet('Rules: Configurable filters (sender domain, subject keywords, file type) to control auto-ingestion'),
      gap(),

      h2('6.5 ESG Clause Analysis'),
      bullet('ESG rubric: Covers carbon commitments, supplier ethics codes, DEI requirements, modern slavery statements, environmental remediation'),
      bullet('Gap report: Contrast contract ESG language against company ESG policy document'),
      bullet('Regulatory alignment: Flag gaps vs. EU CSRD, SEC ESG disclosure rules, UK Modern Slavery Act'),
      gap(),
      new Paragraph({ children: [new PageBreak()] }),

      // ── 7. Risk Taxonomy ───────────────────────────────────────────────
      h1('7. Risk Taxonomy & Benchmarking Framework'),
      divider(),
      para('The platform operates on a 12-category risk taxonomy covering all major commercial contract risk dimensions. Every flagged clause maps to a category, receives a severity score (1\u201310), and is benchmarked against market norms.'),
      gap(),
      riskTaxTable(),
      gap(),
      new Paragraph({ children: [new PageBreak()] }),

      // ── 8. Use Cases ───────────────────────────────────────────────────
      h1('8. Use Cases & Acceptance Criteria'),
      divider(),
      para('The following 15 use cases define the measurable acceptance criteria for each functional capability. Use cases UC-01 through UC-08 are Must-Have (launch); UC-09 through UC-12 are Should-Have; UC-13 through UC-15 are Nice-to-Have.'),
      gap(),
      useCasesTable(),
      gap(),
      new Paragraph({ children: [new PageBreak()] }),

      // ── 9. Technical Architecture ──────────────────────────────────────
      h1('9. Technical Architecture'),
      divider(),
      para('The platform is designed AI-first with a modular, cloud-native architecture. Each layer is independently scalable, allowing inference workloads to scale separately from storage and web serving. The RAG pipeline is the core technical differentiator \u2014 it continuously learns from new contract data while maintaining tenant isolation and data privacy.'),
      gap(),
      techTable(),
      gap(),
      h3('Non-Functional Requirements'),
      bullet('Availability: 99.9% (Growth/Pro), 99.95% (Enterprise); measured monthly; StatusPage public dashboard'),
      bullet('Scalability: Auto-scale ingestion workers to 1,000 concurrent contracts; LLM request queuing with priority lanes'),
      bullet('Latency: P95 < 60s for 50-page contract ingestion; P95 < 500ms for API responses; P95 < 2s for dashboard load'),
      bullet('Data isolation: Strict tenant isolation at database, vector store, and RAG namespace levels; zero cross-tenant data leakage'),
      bullet('Disaster recovery: RPO < 1 hour; RTO < 4 hours; multi-region active-passive; automated failover testing quarterly'),
      gap(),
      new Paragraph({ children: [new PageBreak()] }),

      // ── 10. Monetization ───────────────────────────────────────────────
      h1('10. Monetization Strategy'),
      divider(),
      para('The platform uses a hybrid Product-Led Growth (PLG) + Sales-Assisted model. A 14-day free trial (no credit card) drives top-of-funnel. Automated upgrade nudges convert trials. Mid-market accounts ($1.5K\u2013$3.5K/month) are closed by a 5-person inside sales team. Enterprise and OEM deals use a traditional field sales motion.'),
      gap(),
      pricingTable(),
      gap(),
      h3('Revenue Projections'),
      bullet('Year 1 target: $2M ARR \u2014 150 Starter + 80 Growth + 25 Professional + 5 Enterprise accounts'),
      bullet('Year 2 target: $8M ARR \u2014 expand into enterprise + law firm OEM channel; reduce CAC via PLG optimization'),
      bullet('Year 3 target: $22M ARR \u2014 international expansion (UK/EU); ESG module launch; 40% revenue from OEM channel'),
      gap(),
      h3('Unit Economics Targets'),
      bullet('CAC Payback: < 9 months (Growth tier); < 12 months (Enterprise)'),
      bullet('Net Revenue Retention: > 120% at 12 months (expansion via user count + feature tier upgrades)'),
      bullet('Gross Margin: > 75% (LLM inference cost managed via prompt optimization + caching + fine-tuned model)'),
      bullet('LTV/CAC: > 4x at 24 months across all tiers'),
      gap(),
      new Paragraph({ children: [new PageBreak()] }),

      // ── 11. KPIs ────────────────────────────────────────────────────────
      h1('11. Success Metrics & KPIs'),
      divider(),
      para('The following KPIs govern product quality, engineering performance, and business health. KPIs are reviewed weekly at team level and monthly at board level. Any KPI trending more than 10% below target triggers an escalation protocol.'),
      gap(),
      kpiTable(),
      gap(),
      new Paragraph({ children: [new PageBreak()] }),

      // ── 12. Compliance & Security ───────────────────────────────────────
      h1('12. Security, Privacy & Compliance'),
      divider(),

      h2('12.1 Data Security'),
      bullet('Encryption: AES-256 at rest (tenant-level key isolation); TLS 1.3 in transit; HSM for Enterprise key management'),
      bullet('Data residency: US, EU (Frankfurt), APAC (Singapore) regions; tenant-selectable at signup'),
      bullet('Zero-retention option: Contracts deleted from all systems (including RAG) within 24 hours of processing; Enterprise feature'),
      bullet('Penetration testing: Annual third-party pen test; critical findings remediated within 30 days; report available under NDA'),
      gap(),

      h2('12.2 Compliance Certifications'),
      bullet('SOC 2 Type II: Target certification within 6 months of launch; annual renewal'),
      bullet('GDPR: Data Processing Agreement (DPA) template available; right to erasure workflow; consent management'),
      bullet('CCPA: Consumer data request portal; data map maintained; privacy-by-design architecture'),
      bullet('HIPAA: Business Associate Agreement (BAA) available on Enterprise tier; PHI handling documentation'),
      bullet('ISO 27001: Target certification Year 2; controls aligned from launch'),
      gap(),

      h2('12.3 AI Ethics & Responsible Use'),
      bullet('Hallucination controls: Confidence scoring on all AI outputs; low-confidence flags require attorney review; no auto-execution without human approval'),
      bullet('Bias monitoring: Monthly audit of risk scoring by contract type and counterparty geography; disparity > 5% triggers review'),
      bullet('Model transparency: Explainability layer explains why each clause was flagged; no black-box outputs'),
      bullet('Human-in-the-loop: All AI redlines are suggestions \u2014 platform never auto-applies changes to contracts'),
      bullet('Data minimization: Only contract text processed by LLM; PII stripped before external API calls where possible'),
      gap(),
      new Paragraph({ children: [new PageBreak()] }),

      // ── 13. Go-to-Market ────────────────────────────────────────────────
      h1('13. Go-to-Market Strategy'),
      divider(),

      h2('13.1 Target Segments (Prioritized)'),
      numbered('Mid-market law firms (20\u2013200 attorneys): Legal ops, practice group leaders \u2014 highest immediate TAM + strong expansion via client referrals'),
      numbered('Procurement teams at $100M\u2013$2B revenue companies: Vendor contract volume is high; CFO pressure on contract risk is intense post-COVID'),
      numbered('In-house legal ops at Series B\u2013D tech companies: Legal ops managers stretched thin; strong PLG fit; referral network via GCs'),
      numbered('CFO offices at PE portfolio companies: Risk visibility at portfolio level; high willingness to pay for risk reduction tools'),
      gap(),

      h2('13.2 Sales Motion'),
      bullet('PLG: Free 14-day trial (5 contracts); automated upgrade nudge at trial day 10; Starter conversion target: 20%'),
      bullet('Inside sales: SDR + AE pairs; target legal ops and procurement directors via LinkedIn + CLOC + ACC communities'),
      bullet('Channel: Law firm OEM partners \u2014 10 anchor firms in Year 1; each firm drives 20\u201350 client seats'),
      bullet('Events: CLOC (legal ops), Procurecon (procurement), CFO Summit \u2014 speaking slots + sponsored workshops'),
      gap(),

      h2('13.3 Content & SEO Strategy'),
      bullet('"Free Contract Risk Checker" \u2014 free tool driving 10K+ monthly visitors; converts to trial at 3%'),
      bullet('Clause library blog: 200+ articles on specific clause types and market standards; top-of-funnel SEO'),
      bullet('Annual "State of Contract Risk" report: Primary research report distributed to 50K+ legal ops/procurement professionals; major PR driver'),
      gap(),
      new Paragraph({ children: [new PageBreak()] }),

      // ── 14. Assumptions & Risks ─────────────────────────────────────────
      h1('14. Assumptions, Risks & Mitigations'),
      divider(),
      new Table({
        width: { size: 9900, type: WidthType.DXA },
        columnWidths: [2800, 1200, 3100, 2800],
        rows: [
          headerRow(['Risk', 'Severity', 'Description', 'Mitigation'], [2800, 1200, 3100, 2800]),
          ...([
            ['LLM Accuracy < 95%', 'High', 'Clause extraction accuracy falls below threshold; attorney trust erodes; churn accelerates', 'Monthly accuracy audit; human-in-the-loop review queue; accuracy SLA in contracts; fine-tuning pipeline maintains quality'],
            ['OpenAI/Anthropic Price Increase', 'Medium', 'LLM inference costs increase 3-5x; margin compression to < 60%; pricing model breaks', 'Multi-provider architecture; fine-tuned open-source model (Llama 3) as fallback; prompt optimization reduces tokens by 40%'],
            ['Big Tech Entrant (Microsoft Copilot for Legal)', 'High', 'Microsoft bundles contract AI into M365; commoditizes core flagging features', 'Own the benchmark corpus moat; deepen procurement + CFO workflows where MS has no expertise; accelerate OEM channel'],
            ['Data Privacy Regulatory Action', 'High', 'Regulator flags LLM processing of privileged legal documents; class action from law firm client', 'Zero-retention mode; on-premise deployment option (Enterprise); DPA with all clients; attorney-client privilege analysis published'],
            ['RAG Corpus Data Quality', 'Medium', 'Benchmark data is unrepresentative; poor quality contracts skew market benchmarks; client trust erodes', 'Attorney-curated corpus curation; quarterly refresh with quality scoring; confidence intervals shown; methodology published'],
            ['Sales Cycle Length', 'Medium', 'Enterprise and law firm deals take 6+ months; cash burn accelerates; PLG revenue insufficient to bridge', 'Double down on PLG for immediate revenue; law firm OEM closes faster than direct; inside sales team targets Growth tier ($1.5K/month) with <2-week cycles'],
          ].map((r, i) => new TableRow({
            children: r.map((c, j) => cell(c, {
              fill: i % 2 === 0 ? C.gray : C.white,
              w: [2800, 1200, 3100, 2800][j], size: 17,
              color: j === 1 ? (c === 'High' ? C.red : C.orange) : C.dark,
              bold: j === 0 || j === 1
            }))
          })))
        ]
      }),
      gap(),
      new Paragraph({ children: [new PageBreak()] }),

      // ── Appendix ──────────────────────────────────────────────────────
      h1('Appendix: Glossary & Reference'),
      divider(),
      h3('Key Terms'),
      bullet('RAG (Retrieval-Augmented Generation): AI technique that grounds LLM responses in retrieved documents, dramatically reducing hallucinations in domain-specific applications'),
      bullet('LoRA (Low-Rank Adaptation): Parameter-efficient fine-tuning method for LLMs; enables domain adaptation at 1/10th the cost of full fine-tuning'),
      bullet('CUAD (Contract Understanding Atticus Dataset): 510 commercial contracts, 13K+ expert annotations; primary public training dataset for legal AI'),
      bullet('CLM (Contract Lifecycle Management): Software category managing contract creation, execution, and post-signature obligations'),
      bullet('Redline: Industry term for proposed contract changes marked up in tracked-changes format'),
      bullet('MoSCoW: Prioritization framework \u2014 Must Have, Should Have, Could Have, Won\'t Have'),
      bullet('PLG (Product-Led Growth): Go-to-market strategy where the product itself drives customer acquisition and expansion'),
      bullet('NRR (Net Revenue Retention): Revenue retained + expanded from existing customers; > 100% indicates expansion revenue exceeds churn'),
      gap(),
      h3('Referenced Standards & Regulations'),
      bullet('GDPR: EU General Data Protection Regulation \u2014 governs processing of EU resident data'),
      bullet('CCPA: California Consumer Privacy Act \u2014 US state privacy law applicable to California residents'),
      bullet('SOC 2 Type II: Service Organization Control audit standard for security, availability, confidentiality, processing integrity, and privacy'),
      bullet('HIPAA: Health Insurance Portability and Accountability Act \u2014 governs PHI handling in healthcare contracts'),
      bullet('EU CSRD: Corporate Sustainability Reporting Directive \u2014 mandates ESG disclosure for large EU companies (impacts ESG clause module)'),
      gap(),

      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 400, after: 100 },
        children: [new TextRun({ text: '\u2014 End of Specification Document \u2014', size: 22, italics: true, color: C.midgray, font: 'Arial' })]
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 0, after: 0 },
        children: [new TextRun({ text: 'AI Contract Risk Analyzer  |  2026 Gold Standard Enterprise Specification  |  Version 1.0', size: 18, color: C.midgray, font: 'Arial' })]
      }),
    ]
  }]
});

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync('/Volumes/home/ContractRiskEdge/output/AI_Contract_Risk_Analyzer_Spec_2026.docx', buffer);
  console.log('DOCX written successfully');
});
