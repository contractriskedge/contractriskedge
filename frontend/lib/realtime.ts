/**
 * Realtime WebSocket client for ContractRiskEdge.
 *
 * Provides:
 * - Automatic reconnection with exponential backoff
 * - Auth token injection and refresh on reconnect
 * - Event subscription with topic-based filtering
 * - Delivery acknowledgement (ACK protocol)
 * - Replay cursor persistence (localStorage)
 * - Reconnect replay of missed events
 * - Connection state tracking
 * - Heartbeat keepalive
 * - Visibility API pause/resume (tab hidden → disconnect, tab visible → reconnect)
 * - Tab focus awareness (no reconnect loops on focus)
 * - Connection ownership guard (prevents duplicate connections)
 * - Duplicate connect prevention metrics
 * - Route transition persistence (survives SPA navigation)
 *
 * Usage:
 *   const client = new RealtimeClient({
 *     getToken: () => getAccessTokenSilently(),
 *     onEvent: (event) => handleEvent(event),
 *   });
 *   await client.connect();
 *   client.subscribe(["review.*", "notification.*"]);
 *
 *   // Later:
 *   client.disconnect();
 */

export type RealtimeEvent = {
  type: string;
  event_id?: string;
  event_version?: string;
  sequence_id?: number;
  data?: unknown;
  timestamp?: number;
  replayed?: boolean;
};

export type ConnectionState =
  | "disconnected"
  | "connecting"
  | "connected"
  | "reconnecting"
  | "failed";

export type RealtimeOptions = {
  /** Function that returns a fresh JWT token. Called on connect and reconnect. */
  getToken: () => Promise<string>;
  /** Callback for every event received. */
  onEvent: (event: RealtimeEvent) => void;
  /** Callback for connection state changes. */
  onStateChange?: (state: ConnectionState) => void;
  /** Topics to subscribe to on connect. Default: all events. */
  topics?: string[];
  /** Base URL for the WebSocket endpoint. */
  wsUrl?: string;
  /** Maximum reconnection attempts before giving up. Default: 10. */
  maxReconnectAttempts?: number;
  /** Tenant ID for scoping the replay cursor in localStorage.
   *  When set, the cursor is stored as "ws_last_sequence:{tenant_id}:{user_id}"
   *  instead of the global "ws_last_sequence". This prevents cross-tenant and
   *  cross-user event leakage in multi-tab or shared-device scenarios. */
  tenantId?: string;
  /** User ID for further scoping the replay cursor alongside tenant_id.
   *  When both tenantId and userId are set, the cursor is stored as
   *  "ws_last_sequence:{tenant_id}:{user_id}". This prevents cross-user
   *  replay contamination on shared devices or during impersonation. */
  userId?: string;
  /** Unique connection owner ID for duplicate prevention. When set, only
   *  the most recent connection with the same owner ID is kept alive.
   *  This prevents stale connections from older route renders. */
  connectionOwnerId?: string;
};

const RECONNECT_BASE_DELAY = 1000; // 1 second
const RECONNECT_MAX_DELAY = 30_000; // 30 seconds
const HEARTBEAT_INTERVAL = 30_000; // 30 seconds
const DEFAULT_MAX_RECONNECT = 10;

// ── Connection Ownership Registry ─────────────────────────────────
//
// Prevents duplicate WebSocket connections from the same owner.
// When a new connection is created with the same ownerId, the previous
// one is disconnected first. This handles:
// - Route transitions that remount the provider
// - React StrictMode double-mounts in development
// - Accidental multiple getRealtimeClient calls

const connectionOwnership = new Map<string, RealtimeClient>();

// ── Metrics ───────────────────────────────────────────────────────

export type RealtimeMetrics = {
  /** Total number of connect() calls ever made. */
  totalConnectCalls: number;
  /** Total number of reconnections. */
  totalReconnects: number;
  /** Total number of intentional disconnects. */
  totalDisconnects: number;
  /** Current connection state. */
  currentState: ConnectionState;
  /** Number of times the connection was paused due to visibility. */
  visibilityPauses: number;
  /** Number of times the connection was resumed due to visibility. */
  visibilityResumes: number;
  /** Number of duplicate connection attempts prevented. */
  duplicatePreventions: number;
  /** Timestamp of the last connect call. */
  lastConnectTime: number | null;
};

const metrics: RealtimeMetrics = {
  totalConnectCalls: 0,
  totalReconnects: 0,
  totalDisconnects: 0,
  currentState: "disconnected",
  visibilityPauses: 0,
  visibilityResumes: 0,
  duplicatePreventions: 0,
  lastConnectTime: null,
};

export function getRealtimeMetrics(): RealtimeMetrics {
  return { ...metrics };
}

export class RealtimeClient {
  private ws: WebSocket | null = null;
  private state: ConnectionState = "disconnected";
  private reconnectAttempts = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  private intentionalClose = false;
  private lastSequenceId = 0;
  /** Tracks if the connection was paused due to tab visibility. */
  private pausedForVisibility = false;
  /** Bound event listener for visibility change (so we can remove it). */
  private boundVisibilityHandler: (() => void) | null = null;

  private getToken: () => Promise<string>;
  private onEvent: (event: RealtimeEvent) => void;
  private onStateChange?: (state: ConnectionState) => void;
  private topics: string[];
  private wsUrl: string;
  private maxReconnectAttempts: number;
  private tenantId: string | undefined;
  private userId: string | undefined;
  private sequenceStorageKey: string;
  private connectionOwnerId: string | undefined;

  constructor(options: RealtimeOptions) {
    this.getToken = options.getToken;
    this.onEvent = options.onEvent;
    this.onStateChange = options.onStateChange;
    this.topics = options.topics ?? [];
    this.wsUrl = options.wsUrl ?? `${this.getBaseWsUrl()}/api/v1/ws/events`;
    this.maxReconnectAttempts = options.maxReconnectAttempts ?? DEFAULT_MAX_RECONNECT;
    this.tenantId = options.tenantId;
    this.userId = options.userId;
    this.connectionOwnerId = options.connectionOwnerId;

    // ── Connection ownership guard ──────────────────────────────
    // If a previous client with the same ownerId exists, disconnect it.
    // This prevents duplicate connections from stale component instances.
    if (this.connectionOwnerId) {
      const existing = connectionOwnership.get(this.connectionOwnerId);
      if (existing && existing !== this) {
        metrics.duplicatePreventions++;
        console.debug(
          `[Realtime] Ownership conflict for "${this.connectionOwnerId}" — disconnecting stale client`,
        );
        existing.disconnect();
      }
      connectionOwnership.set(this.connectionOwnerId, this);
    }

    // User- and tenant-scoped replay cursor:
    //   "ws_last_sequence:{tenant_id}:{user_id}"
    //
    // This prevents:
    // - Cross-tenant replay contamination (multi-tab, different tenants)
    // - Cross-user replay restoration (shared devices, impersonation)
    // - Stale cursor from a different session overwriting current state
    //
    // The most specific scope wins:
    //   tenant + user  → "ws_last_sequence:{tenant}:{user}"
    //   tenant only    → "ws_last_sequence:{tenant}"
    //   neither        → "ws_last_sequence" (legacy fallback)
    if (options.tenantId && options.userId) {
      this.sequenceStorageKey = `ws_last_sequence:${options.tenantId}:${options.userId}`;
    } else if (options.tenantId) {
      this.sequenceStorageKey = `ws_last_sequence:${options.tenantId}`;
    } else {
      this.sequenceStorageKey = "ws_last_sequence";
    }

    // Restore last sequence ID from localStorage for replay on reconnect
    this.lastSequenceId = this.loadSequenceId();
  }

  /**
   * Connect to the WebSocket server.
   * Authenticates with JWT, subscribes to topics, and starts heartbeat.
   */
  async connect(): Promise<void> {
    metrics.totalConnectCalls++;
    metrics.lastConnectTime = Date.now();

    // If paused for visibility, don't actually connect — wait for resume
    if (this.pausedForVisibility) {
      console.debug("[Realtime] Suppressed connect — paused for visibility");
      return;
    }

    if (this.ws?.readyState === WebSocket.OPEN || this.ws?.readyState === WebSocket.CONNECTING) {
      return; // Already connected or connecting
    }

    this.intentionalClose = false;
    this.setState("connecting");

    try {
      const token = await this.getToken();
      this.ws = new WebSocket(this.wsUrl);

      this.ws.onopen = () => {
        this.reconnectAttempts = 0;
        this.setState("connected");

        // Send auth with replay cursor
        this.send({
          type: "auth",
          token,
          last_sequence_id: this.lastSequenceId > 0 ? this.lastSequenceId : undefined,
        });

        // Subscribe to topics if specified
        if (this.topics.length > 0) {
          this.send({ type: "subscribe", topics: this.topics });
        }

        // Start heartbeat
        this.startHeartbeat();

        // Register visibility handler for tab focus awareness
        this.registerVisibilityHandler();
      };

      this.ws.onmessage = (event: MessageEvent) => {
        try {
          const msg: RealtimeEvent = JSON.parse(event.data);

          // Track sequence ID for replay cursor
          if (msg.sequence_id && msg.sequence_id > this.lastSequenceId) {
            this.lastSequenceId = msg.sequence_id;
            this.persistSequenceId(this.lastSequenceId);
          }

          // Auto-acknowledge events with event_id
          if (msg.event_id) {
            this.send({ type: "ack", event_id: msg.event_id });
          }

          // Handle control messages
          if (msg.type === "pong" || msg.type === "heartbeat") {
            return; // Silently consume
          }
          if (msg.type === "connected") {
            console.debug("[Realtime] Connected:", msg.data);
            return;
          }
          if (msg.type === "subscribed") {
            console.debug("[Realtime] Subscribed:", msg.data);
            return;
          }
          if (msg.type === "replay_start" || msg.type === "replay_complete") {
            console.debug("[Realtime] Replay:", msg.type, msg.data);
            return;
          }
          if (msg.type === "replay_error") {
            console.warn("[Realtime] Replay error:", msg.data);
            return;
          }

          // Dispatch to event handler
          this.onEvent(msg);
        } catch (err) {
          console.warn("[Realtime] Failed to parse message:", err);
        }
      };

      this.ws.onclose = (event) => {
        this.stopHeartbeat();
        // If the close was clean (code 1000) or the endpoint doesn't exist
        // (code 1006 with no prior open), don't reconnect.
        const neverOpened = event.code === 1006 && this.reconnectAttempts === 0;
        if (!this.intentionalClose && !this.pausedForVisibility && !neverOpened) {
          metrics.totalReconnects++;
          this.scheduleReconnect();
        } else {
          if (neverOpened) {
            console.warn("[Realtime] WebSocket endpoint not available — realtime features disabled");
          }
          this.setState("disconnected");
        }
      };

      this.ws.onerror = () => {
        // Error is followed by onclose — don't log or reconnect here,
        // let onclose handle the decision.
      };
    } catch (err) {
      console.error("[Realtime] Failed to connect:", err);
      this.setState("failed");
      this.scheduleReconnect();
    }
  }

  /**
   * Disconnect intentionally. No reconnect will be attempted.
   */
  disconnect(): void {
    metrics.totalDisconnects++;
    this.intentionalClose = true;
    this.pausedForVisibility = false;
    this.stopHeartbeat();
    this.clearReconnectTimer();
    this.removeVisibilityHandler();
    if (this.ws) {
      this.ws.close(1000, "Client disconnected");
      this.ws = null;
    }
    this.setState("disconnected");

    // Release ownership
    if (this.connectionOwnerId) {
      connectionOwnership.delete(this.connectionOwnerId);
    }
  }

  /**
   * Pause the connection without triggering reconnect.
   * Used when the tab becomes hidden (Visibility API).
   * The connection will be restored on resume().
   */
  pause(): void {
    if (this.pausedForVisibility) return;
    this.pausedForVisibility = true;
    metrics.visibilityPauses++;

    if (this.state === "connected" || this.state === "connecting" || this.state === "reconnecting") {
      console.debug("[Realtime] Pausing connection — tab hidden");
      this.intentionalClose = true; // Prevent reconnect on close
      this.stopHeartbeat();
      this.clearReconnectTimer();
      if (this.ws) {
        this.ws.close(1000, "Tab hidden");
        this.ws = null;
      }
      this.setState("disconnected");
    }
  }

  /**
   * Resume the connection after a pause.
   * Used when the tab becomes visible again.
   */
  resume(): void {
    if (!this.pausedForVisibility) return;
    this.pausedForVisibility = false;
    metrics.visibilityResumes++;
    console.debug("[Realtime] Resuming connection — tab visible");
    this.connect();
  }

  /**
   * Returns whether the connection is currently paused for visibility.
   */
  isPaused(): boolean {
    return this.pausedForVisibility;
  }

  /**
   * Update topic subscriptions.
   * Sends a subscribe message to the server.
   */
  subscribe(topics: string[]): void {
    this.topics = topics;
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.send({ type: "subscribe", topics });
    }
  }

  /**
   * Get the current connection state.
   */
  getState(): ConnectionState {
    return this.state;
  }

  /**
   * Get the last known sequence ID (for external persistence).
   */
  getLastSequenceId(): number {
    return this.lastSequenceId;
  }

  /**
   * Register the visibility change handler.
   * Pauses connection when tab is hidden, resumes when visible.
   */
  private registerVisibilityHandler(): void {
    this.removeVisibilityHandler();
    this.boundVisibilityHandler = () => {
      if (document.hidden) {
        this.pause();
      } else {
        this.resume();
      }
    };
    document.addEventListener("visibilitychange", this.boundVisibilityHandler);
  }

  /**
   * Remove the visibility change handler.
   */
  private removeVisibilityHandler(): void {
    if (this.boundVisibilityHandler) {
      document.removeEventListener("visibilitychange", this.boundVisibilityHandler);
      this.boundVisibilityHandler = null;
    }
  }

  // ── Private ──────────────────────────────────────────────────

  private send(data: Record<string, unknown>): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  private setState(state: ConnectionState): void {
    this.state = state;
    this.onStateChange?.(state);
  }

  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error("[Realtime] Max reconnect attempts reached");
      this.setState("failed");
      return;
    }

    this.setState("reconnecting");
    this.reconnectAttempts++;

    // Exponential backoff with jitter
    const delay = Math.min(
      RECONNECT_BASE_DELAY * Math.pow(2, this.reconnectAttempts - 1) +
        Math.random() * 1000,
      RECONNECT_MAX_DELAY,
    );

    console.debug(
      `[Realtime] Reconnecting in ${Math.round(delay / 1000)}s (attempt ${this.reconnectAttempts})`,
    );

    this.reconnectTimer = setTimeout(() => {
      this.connect();
    }, delay);
  }

  private clearReconnectTimer(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  private startHeartbeat(): void {
    this.stopHeartbeat();
    this.heartbeatTimer = setInterval(() => {
      this.send({ type: "ping" });
    }, HEARTBEAT_INTERVAL);
  }

  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  private loadSequenceId(): number {
    try {
      const stored = localStorage.getItem(this.sequenceStorageKey);
      return stored ? parseInt(stored, 10) || 0 : 0;
    } catch {
      return 0;
    }
  }

  private persistSequenceId(id: number): void {
    try {
      localStorage.setItem(this.sequenceStorageKey, String(id));
    } catch {
      // localStorage may be unavailable (private browsing, etc.)
    }
  }

  private getBaseWsUrl(): string {
    if (typeof window !== "undefined") {
      const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
      return `${proto}//${window.location.host}`;
    }
    return "ws://localhost:3000";
  }
}

/**
 * Singleton manager for the RealtimeClient.
 * Ensures only one WebSocket connection exists per page.
 *
 * Uses connectionOwnerId for ownership tracking — if a new client
 * claims the same ownerId, the previous one is disconnected.
 */
let globalClient: RealtimeClient | null = null;
let globalOwnerId: string | null = null;

export function getRealtimeClient(options: RealtimeOptions): RealtimeClient {
  const ownerId = options.connectionOwnerId ?? "default";

  // If the ownerId changed, disconnect the old client and create a new one
  if (globalClient && globalOwnerId !== ownerId) {
    console.debug(`[Realtime] Owner changed from "${globalOwnerId}" to "${ownerId}" — replacing client`);
    globalClient.disconnect();
    globalClient = null;
    globalOwnerId = null;
  }

  if (!globalClient) {
    globalClient = new RealtimeClient(options);
    globalOwnerId = ownerId;
  }
  return globalClient;
}

export function disconnectRealtimeClient(): void {
  if (globalClient) {
    globalClient.disconnect();
    globalClient = null;
    globalOwnerId = null;
  }
}

/**
 * Pause the global realtime client (e.g., when tab is hidden).
 */
export function pauseRealtimeClient(): void {
  globalClient?.pause();
}

/**
 * Resume the global realtime client (e.g., when tab is visible).
 */
export function resumeRealtimeClient(): void {
  globalClient?.resume();
}
