/**
 * Contract Detail Workspace — barrel exports.
 */

export { ContractDetailWorkspace } from "./ContractDetailWorkspace";
export { DocumentViewer } from "./DocumentViewer";
export { AiFindingsPanel } from "./AiFindingsPanel";
export { MetadataPanel } from "./MetadataPanel";
export { ActivityTimelinePanel } from "./ActivityTimelinePanel";
export { CommentingPanel } from "./CommentingPanel";
export type * from "./types";
export {
  useContractDetail,
  useContractFindings,
  useContractClauses,
  useContractCompliance,
  useContractActivity,
  useContractComments,
  useContractObligations,
  useContractVersions,
  useResolveFinding,
  useDismissFinding,
  useAddComment,
  useResolveComment,
  contractDetailKeys,
} from "./hooks";
