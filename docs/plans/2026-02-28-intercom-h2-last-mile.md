# Intercom H2 Last Mile — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use clavain:executing-plans to implement this plan task-by-task.

**Goal:** Wire 5 container write tools + gate approval inline buttons + budget/run event actions + demarch_research to complete Intercom's H2 bidirectional agency participation.

**Architecture:** All write tools use the existing `queryKernel()` IPC bridge from containers. The host-side IPC dispatcher in `ipc.rs` already routes write query types (`create_issue`, `update_issue`, etc.) to `DemarchAdapter::execute_write()`. We're adding the container surface (TypeScript wrapper functions + MCP tool declarations) and the Telegram callback handling for gate/budget events.

**Tech Stack:** TypeScript (container tools, MCP tools), Rust (Telegram callback handler, event notification buttons), Zod (MCP param validation), Grammy patterns (inline keyboards via raw Telegram Bot API)

**Prior Learnings:**
- `docs/solutions/database-issues/toctou-gate-check-cas-dispatch-intercore-20260221.md` — Gate approval must be idempotent (first-reply-wins). Use CAS guard: check gate status before writing, reject if already resolved.
- `docs/solutions/patterns/critical-patterns.md` — MCP tool patterns for container agents.

---

### Task 1: Add write wrapper functions to demarch-tools.ts

**Files:**
- Modify: `apps/intercom/container/shared/demarch-tools.ts`

**Step 1: Add the 5 write functions after existing read functions**

Append to `apps/intercom/container/shared/demarch-tools.ts` after line 51:

```typescript
// --- Write operations (H2) ---

export function demarchCreateIssue(
  _ctx: IpcContext,
  title: string,
  description?: string,
  priority?: string,
  issueType?: string,
  labels?: string[],
): Promise<string> {
  const params: Record<string, unknown> = { title };
  if (description) params.description = description;
  if (priority) params.priority = priority;
  if (issueType) params.issue_type = issueType;
  if (labels) params.labels = labels;
  return queryKernel('create_issue', params);
}

export function demarchUpdateIssue(
  _ctx: IpcContext,
  id: string,
  status?: string,
  priority?: string,
  title?: string,
  description?: string,
  notes?: string,
): Promise<string> {
  const params: Record<string, unknown> = { id };
  if (status) params.status = status;
  if (priority) params.priority = priority;
  if (title) params.title = title;
  if (description) params.description = description;
  if (notes) params.notes = notes;
  return queryKernel('update_issue', params);
}

export function demarchCloseIssue(
  _ctx: IpcContext,
  id: string,
  reason?: string,
): Promise<string> {
  const params: Record<string, unknown> = { id };
  if (reason) params.reason = reason;
  return queryKernel('close_issue', params);
}

export function demarchStartRun(
  _ctx: IpcContext,
  title?: string,
  description?: string,
): Promise<string> {
  const params: Record<string, unknown> = {};
  if (title) params.title = title;
  if (description) params.description = description;
  return queryKernel('start_run', params);
}

export function demarchApproveGate(
  _ctx: IpcContext,
  gateId: string,
  reason?: string,
): Promise<string> {
  const params: Record<string, unknown> = { gate_id: gateId };
  if (reason) params.reason = reason;
  return queryKernel('approve_gate', params);
}
```

**Step 2: Verify TypeScript compiles**

Run: `cd apps/intercom && npx tsc --noEmit`
Expected: No errors (new functions follow exact same pattern as existing reads)

**Step 3: Commit**

```bash
git add apps/intercom/container/shared/demarch-tools.ts
git commit -m "feat(intercom): add 5 Demarch write tool wrappers for container agents"
```

---

### Task 2: Add write MCP tool declarations for Claude runtime

**Files:**
- Modify: `apps/intercom/container/agent-runner/src/ipc-mcp-stdio.ts`

**Step 1: Add 5 write MCP tools after the existing read tools**

Insert before the `// Start the stdio transport` line (line 407) in `ipc-mcp-stdio.ts`:

```typescript
// --- Demarch Write Tools (H2) ---

server.tool(
  'demarch_create_issue',
  'Create a new work item (bead) in the Demarch issue tracker. Returns JSON with the new bead ID.',
  {
    title: z.string().describe('Title for the new issue (required)'),
    description: z.string().optional().describe('Detailed description of the issue'),
    priority: z.string().optional().describe('Priority: 0 (critical) through 4 (backlog). Default: 2'),
    issue_type: z.string().optional().describe('Type: task, feature, bug, epic. Default: task'),
    labels: z.array(z.string()).optional().describe('Labels to attach to the issue'),
  },
  async (args) => {
    const params: Record<string, unknown> = { title: args.title };
    if (args.description) params.description = args.description;
    if (args.priority) params.priority = args.priority;
    if (args.issue_type) params.issue_type = args.issue_type;
    if (args.labels) params.labels = args.labels;
    const result = await queryKernel('create_issue', params);
    return { content: [{ type: 'text' as const, text: result }] };
  },
);

server.tool(
  'demarch_update_issue',
  'Update an existing work item (bead). Only provided fields are changed.',
  {
    id: z.string().describe('Bead ID to update (required, e.g., "beads-abc123")'),
    status: z.string().optional().describe('New status: open, in_progress, closed'),
    priority: z.string().optional().describe('New priority: 0-4'),
    title: z.string().optional().describe('New title'),
    description: z.string().optional().describe('New description'),
    notes: z.string().optional().describe('Append notes to the issue'),
  },
  async (args) => {
    const params: Record<string, unknown> = { id: args.id };
    if (args.status) params.status = args.status;
    if (args.priority) params.priority = args.priority;
    if (args.title) params.title = args.title;
    if (args.description) params.description = args.description;
    if (args.notes) params.notes = args.notes;
    const result = await queryKernel('update_issue', params);
    return { content: [{ type: 'text' as const, text: result }] };
  },
);

server.tool(
  'demarch_close_issue',
  'Close a work item (bead), marking it as completed.',
  {
    id: z.string().describe('Bead ID to close (required)'),
    reason: z.string().optional().describe('Reason for closing (e.g., "completed", "duplicate")'),
  },
  async (args) => {
    const params: Record<string, unknown> = { id: args.id };
    if (args.reason) params.reason = args.reason;
    const result = await queryKernel('close_issue', params);
    return { content: [{ type: 'text' as const, text: result }] };
  },
);

server.tool(
  'demarch_start_run',
  'Start a new sprint/run in the Demarch kernel. This is a policy-governing action that may require human confirmation.',
  {
    title: z.string().optional().describe('Title for the new run'),
    description: z.string().optional().describe('Description of the run goals'),
  },
  async (args) => {
    const params: Record<string, unknown> = {};
    if (args.title) params.title = args.title;
    if (args.description) params.description = args.description;
    const result = await queryKernel('start_run', params);
    return { content: [{ type: 'text' as const, text: result }] };
  },
);

server.tool(
  'demarch_approve_gate',
  'Approve or advance a gate in the current sprint. This is a policy-governing action that may require human confirmation.',
  {
    gate_id: z.string().describe('Gate ID to approve (required)'),
    reason: z.string().optional().describe('Reason for approval'),
  },
  async (args) => {
    const params: Record<string, unknown> = { gate_id: args.gate_id };
    if (args.reason) params.reason = args.reason;
    const result = await queryKernel('approve_gate', params);
    return { content: [{ type: 'text' as const, text: result }] };
  },
);
```

**Step 2: Verify TypeScript compiles**

Run: `cd apps/intercom && npx tsc --noEmit`
Expected: No errors

**Step 3: Commit**

```bash
git add apps/intercom/container/agent-runner/src/ipc-mcp-stdio.ts
git commit -m "feat(intercom): add 5 Demarch write MCP tools for Claude container agents"
```

---

### Task 3: Add demarch_research read tool (H1 completion)

**Files:**
- Modify: `apps/intercom/src/query-handlers.ts`
- Modify: `apps/intercom/container/shared/demarch-tools.ts`
- Modify: `apps/intercom/container/agent-runner/src/ipc-mcp-stdio.ts`

**Step 1: Add research handler to query-handlers.ts**

Insert before the `handleQuery` function (before line 186):

```typescript
function handleResearch(params: Record<string, unknown>): QueryResponse {
  if (!isCliAvailable('ic')) return { status: 'error', result: STANDALONE_MSG };

  const query = params.query as string | undefined;
  if (!query) {
    return { status: 'error', result: 'research requires a query parameter' };
  }

  const args = ['discovery', 'search', '--json', query];
  const result = execCli('ic', args);
  if (result === null) {
    return {
      status: 'error',
      result: 'Research tool not available — ic discovery subcommand may not exist yet.',
    };
  }
  return { status: 'ok', result };
}
```

**Step 2: Add route in handleQuery switch statement**

In `handleQuery`, add before the `default:` case (line 209):

```typescript
    case 'research':
      return handleResearch(params);
```

**Step 3: Add wrapper function to demarch-tools.ts**

Append to `apps/intercom/container/shared/demarch-tools.ts`:

```typescript
export function demarchResearch(_ctx: IpcContext, query: string): Promise<string> {
  return queryKernel('research', { query });
}
```

**Step 4: Add MCP tool declaration to ipc-mcp-stdio.ts**

Insert with the other Demarch read tools (after `demarch_run_events`, before the write tools section):

```typescript
server.tool(
  'demarch_research',
  'Search for research findings, discoveries, and knowledge in the Demarch platform.',
  {
    query: z.string().describe('Search query — keywords or topic to research'),
  },
  async (args) => {
    const result = await queryKernel('research', { query: args.query });
    return { content: [{ type: 'text' as const, text: result }] };
  },
);
```

**Step 5: Verify TypeScript compiles**

Run: `cd apps/intercom && npx tsc --noEmit`
Expected: No errors

**Step 6: Commit**

```bash
git add apps/intercom/src/query-handlers.ts apps/intercom/container/shared/demarch-tools.ts apps/intercom/container/agent-runner/src/ipc-mcp-stdio.ts
git commit -m "feat(intercom): add demarch_research tool — completes H1 read toolkit"
```

---

### Task 4: Add Telegram inline keyboard support to send_message

**Files:**
- Modify: `apps/intercom/rust/intercomd/src/telegram.rs`

This task adds optional `reply_markup` support to the existing `send_message` function so events can send messages with inline buttons.

**Step 1: Add InlineKeyboard types**

Insert after `TelegramEditResponse` (after line 90 in `telegram.rs`):

```rust
/// Inline keyboard button for Telegram Bot API.
#[derive(Debug, Clone, Serialize)]
pub struct InlineKeyboardButton {
    pub text: String,
    pub callback_data: String,
}

/// Inline keyboard markup (array of button rows).
#[derive(Debug, Clone, Serialize)]
pub struct InlineKeyboardMarkup {
    pub inline_keyboard: Vec<Vec<InlineKeyboardButton>>,
}

/// Extended send request with optional inline keyboard.
#[derive(Debug, Clone, Deserialize)]
pub struct TelegramSendWithButtonsRequest {
    pub jid: String,
    pub text: String,
    pub reply_markup: Option<InlineKeyboardMarkup>,
}
```

**Step 2: Add send_message_with_buttons method**

Add a new method to `TelegramBridge` that extends `send_message` with optional `reply_markup`. Insert after the existing `send_message` method (after line 283):

```rust
    /// Send a message with optional inline keyboard buttons.
    /// Falls back to plain text if reply_markup is None.
    pub async fn send_message_with_buttons(
        &self,
        request: TelegramSendWithButtonsRequest,
    ) -> anyhow::Result<TelegramSendResponse> {
        if request.reply_markup.is_none() {
            return self
                .send_message(TelegramSendRequest {
                    jid: request.jid,
                    text: request.text,
                })
                .await;
        }

        let token = self
            .bot_token
            .as_ref()
            .ok_or_else(|| anyhow!("TELEGRAM_BOT_TOKEN is not set for intercomd"))?;

        let chat_id = normalize_chat_id(&request.jid);
        let endpoint = format!("{TELEGRAM_API_BASE}/bot{token}/sendMessage");

        let mut body = serde_json::json!({
            "chat_id": chat_id,
            "text": &request.text,
        });
        if let Some(markup) = &request.reply_markup {
            body["reply_markup"] = serde_json::to_value(markup)
                .context("failed to serialize InlineKeyboardMarkup")?;
        }

        let response = self
            .client
            .post(&endpoint)
            .json(&body)
            .send()
            .await
            .context("failed to call Telegram sendMessage")?;

        let envelope: TelegramApiEnvelope = response
            .json()
            .await
            .context("failed to parse Telegram sendMessage response")?;
        if !envelope.ok {
            return Err(anyhow!(envelope.description.unwrap_or_else(|| {
                "Telegram sendMessage returned ok=false".to_string()
            })));
        }

        let message_id = envelope
            .result
            .as_ref()
            .and_then(|v| v.get("message_id"))
            .and_then(|v| v.as_i64())
            .map(|id| id.to_string())
            .unwrap_or_default();

        Ok(TelegramSendResponse {
            ok: true,
            error: None,
            message_ids: vec![message_id],
            chunks_planned: 1,
            chunks_sent: 1,
            chunk_lengths: vec![request.text.chars().count()],
            parity: TelegramSendParity {
                max_chars_per_chunk: TELEGRAM_MAX_TEXT_CHARS,
                all_chunks_within_limit: request.text.chars().count() <= TELEGRAM_MAX_TEXT_CHARS,
            },
        })
    }
```

**Step 3: Add callback query answer method**

Add after `send_message_with_buttons`:

```rust
    /// Answer a Telegram callback query (acknowledge button press).
    pub async fn answer_callback_query(
        &self,
        callback_query_id: &str,
        text: Option<&str>,
    ) -> anyhow::Result<()> {
        let token = self
            .bot_token
            .as_ref()
            .ok_or_else(|| anyhow!("TELEGRAM_BOT_TOKEN is not set for intercomd"))?;

        let endpoint = format!("{TELEGRAM_API_BASE}/bot{token}/answerCallbackQuery");
        let mut body = serde_json::json!({
            "callback_query_id": callback_query_id,
        });
        if let Some(t) = text {
            body["text"] = serde_json::json!(t);
        }

        self.client
            .post(&endpoint)
            .json(&body)
            .send()
            .await
            .context("failed to call Telegram answerCallbackQuery")?;

        Ok(())
    }
```

**Step 4: Verify Rust compiles**

Run: `cd apps/intercom && cargo check --manifest-path rust/Cargo.toml --workspace`
Expected: No errors

**Step 5: Commit**

```bash
git add apps/intercom/rust/intercomd/src/telegram.rs
git commit -m "feat(intercom): add inline keyboard + callback query support to Telegram bridge"
```

---

### Task 5: Update event notifications to use inline buttons

**Files:**
- Modify: `apps/intercom/rust/intercomd/src/events.rs`
- Modify: `apps/intercom/rust/intercomd/src/ipc.rs` (IpcDelegate trait)

This task changes event notifications from plain text to messages with inline buttons for actionable events.

**Step 1: Extend IpcDelegate trait with button-aware send**

In `ipc.rs`, add to the `IpcDelegate` trait (after line 51):

```rust
    /// Send a message with optional inline keyboard buttons.
    /// Default implementation ignores buttons and sends plain text.
    fn send_message_with_buttons(
        &self,
        chat_jid: &str,
        text: &str,
        sender: Option<&str>,
        reply_markup: Option<crate::telegram::InlineKeyboardMarkup>,
    ) {
        // Default: ignore buttons, send plain text
        self.send_message(chat_jid, text, sender);
    }
```

Update `LogOnlyDelegate` impl to include the default.

**Step 2: Add button builders to events.rs**

Add after the imports (after line 17):

```rust
use crate::telegram::{InlineKeyboardButton, InlineKeyboardMarkup};

/// Build inline keyboard for gate approval.
fn gate_approval_buttons(gate_id: &str) -> InlineKeyboardMarkup {
    InlineKeyboardMarkup {
        inline_keyboard: vec![vec![
            InlineKeyboardButton {
                text: "✅ Approve".to_string(),
                callback_data: format!("approve:{gate_id}"),
            },
            InlineKeyboardButton {
                text: "❌ Reject".to_string(),
                callback_data: format!("reject:{gate_id}"),
            },
            InlineKeyboardButton {
                text: "⏸ Defer".to_string(),
                callback_data: format!("defer:{gate_id}"),
            },
        ]],
    }
}

/// Build inline keyboard for budget exceeded.
fn budget_action_buttons(run_id: &str) -> InlineKeyboardMarkup {
    InlineKeyboardMarkup {
        inline_keyboard: vec![vec![
            InlineKeyboardButton {
                text: "📈 Extend".to_string(),
                callback_data: format!("extend:{run_id}"),
            },
            InlineKeyboardButton {
                text: "🛑 Cancel".to_string(),
                callback_data: format!("cancel:{run_id}"),
            },
        ]],
    }
}
```

**Step 3: Change format_notification to return text + optional buttons**

Replace `format_notification` return type from `Option<String>` to a struct:

```rust
struct Notification {
    text: String,
    buttons: Option<InlineKeyboardMarkup>,
}

fn format_notification(&self, event: &KernelEvent) -> Option<Notification> {
    let kind = event
        .kind
        .as_deref()
        .or(event.event_type.as_deref())
        .unwrap_or("unknown");

    match kind {
        "gate.pending" | "gate_pending" => {
            let gate_id = event.gate_id.as_deref().unwrap_or("unknown");
            let run_id = event.run_id.as_deref().unwrap_or("?");
            Some(Notification {
                text: format!(
                    "🚪 Gate approval needed\n\n\
                     Gate: {gate_id}\n\
                     Run: {run_id}"
                ),
                buttons: Some(gate_approval_buttons(gate_id)),
            })
        }
        "budget.exceeded" | "budget_exceeded" => {
            let run_id = event.run_id.as_deref().unwrap_or("?");
            Some(Notification {
                text: format!("💰 Budget alert for run {run_id}\n\nToken budget exceeded."),
                buttons: Some(budget_action_buttons(run_id)),
            })
        }
        "run.completed" | "run_completed" => {
            let run_id = event.run_id.as_deref().unwrap_or("?");
            let reason = event.reason.as_deref().unwrap_or("completed normally");
            Some(Notification {
                text: format!("✅ Run {run_id} completed: {reason}"),
                buttons: None,
            })
        }
        "phase.changed" | "phase_changed" => {
            let run_id = event.run_id.as_deref().unwrap_or("?");
            let phase = event.phase.as_deref().unwrap_or("?");
            Some(Notification {
                text: format!("📋 Run {run_id} phase → {phase}"),
                buttons: None,
            })
        }
        _ => {
            debug!(kind, "Skipping unhandled event type");
            None
        }
    }
}
```

**Step 4: Update poll_events to use button-aware send**

Change the send call in `poll_events` (line 151-152):

```rust
for event in &events {
    if let Some(notif) = self.format_notification(event) {
        self.delegate.send_message_with_buttons(
            notification_jid,
            &notif.text,
            Some("Intercom"),
            notif.buttons,
        );
    }
    // Advance cursor
    if let Some(id) = &event.id {
        self.last_event_id = Some(id.clone());
    }
}
```

**Step 5: Update tests**

Update all `format_notification` test assertions to use the new `Notification` struct:

```rust
#[test]
fn formats_gate_pending() {
    // ... existing setup ...
    let notif = consumer
        .format_notification(&test_event("gate.pending"))
        .unwrap();
    assert!(notif.text.contains("Gate approval needed"));
    assert!(notif.text.contains("gate-review"));
    assert!(notif.buttons.is_some());
    let buttons = notif.buttons.unwrap();
    assert_eq!(buttons.inline_keyboard[0].len(), 3); // Approve, Reject, Defer
    assert!(buttons.inline_keyboard[0][0].callback_data.starts_with("approve:"));
}

#[test]
fn formats_budget_exceeded() {
    // ... existing setup ...
    let notif = consumer
        .format_notification(&test_event("budget.exceeded"))
        .unwrap();
    assert!(notif.text.contains("Budget alert"));
    assert!(notif.buttons.is_some());
    let buttons = notif.buttons.unwrap();
    assert_eq!(buttons.inline_keyboard[0].len(), 2); // Extend, Cancel
}

#[test]
fn formats_run_completed() {
    // ... existing setup ...
    let notif = consumer
        .format_notification(&test_event("run.completed"))
        .unwrap();
    assert!(notif.text.contains("abc123"));
    assert!(notif.buttons.is_none()); // No buttons for info-only events
}
```

**Step 6: Verify Rust compiles and tests pass**

Run: `cd apps/intercom && cargo test --manifest-path rust/Cargo.toml --workspace`
Expected: All tests pass

**Step 7: Commit**

```bash
git add apps/intercom/rust/intercomd/src/events.rs apps/intercom/rust/intercomd/src/ipc.rs
git commit -m "feat(intercom): event notifications with inline keyboard buttons for gate/budget actions"
```

---

### Task 6: Add Telegram callback query handler for gate approval

**Files:**
- Modify: `apps/intercom/rust/intercomd/src/telegram.rs`
- Modify: `apps/intercom/rust/intercomd/src/main.rs` (add route)

This is the critical wiring: when a user presses APPROVE/REJECT/DEFER on a gate notification, the callback routes through to `WriteOperation::ApproveGate`.

**Step 1: Add callback query request/response types**

Insert in `telegram.rs` after the `InlineKeyboardMarkup` types:

```rust
/// Incoming callback query from Telegram (button press).
#[derive(Debug, Clone, Deserialize)]
pub struct TelegramCallbackRequest {
    pub callback_query_id: String,
    pub chat_jid: String,
    pub message_id: String,
    pub sender_id: Option<String>,
    pub sender_name: Option<String>,
    pub data: String,  // e.g., "approve:gate-review"
}

#[derive(Debug, Clone, Serialize)]
pub struct TelegramCallbackResponse {
    pub ok: bool,
    pub action: String,
    pub target_id: String,
    pub result: Option<String>,
    pub error: Option<String>,
}
```

**Step 2: Add callback handler method to TelegramBridge**

```rust
    /// Handle a callback query from an inline keyboard button press.
    /// Parses the callback data, routes to the appropriate Demarch write operation,
    /// edits the original message with the result, and answers the callback.
    pub async fn handle_callback(
        &self,
        request: TelegramCallbackRequest,
        demarch: &intercom_core::DemarchAdapter,
    ) -> anyhow::Result<TelegramCallbackResponse> {
        // Parse callback_data: "action:target_id"
        let parts: Vec<&str> = request.data.splitn(2, ':').collect();
        if parts.len() != 2 {
            self.answer_callback_query(&request.callback_query_id, Some("Invalid action"))
                .await?;
            return Ok(TelegramCallbackResponse {
                ok: false,
                action: request.data.clone(),
                target_id: String::new(),
                result: None,
                error: Some("Invalid callback data format".to_string()),
            });
        }

        let action = parts[0];
        let target_id = parts[1].to_string();
        let sender = request.sender_name.as_deref().unwrap_or("unknown");

        let (write_result, status_text) = match action {
            "approve" => {
                let resp = demarch.execute_write(
                    intercom_core::WriteOperation::ApproveGate {
                        gate_id: Some(target_id.clone()),
                        reason: Some(format!("Approved by {sender} via Telegram")),
                    },
                    true, // gate approval always acts as main
                );
                let ok = resp.status == intercom_core::DemarchStatus::Ok;
                (resp.result, if ok { format!("✅ Gate {target_id} approved by @{sender}") } else { format!("❌ Failed: {}", resp.result) })
            }
            "reject" => {
                let resp = demarch.execute_write(
                    intercom_core::WriteOperation::ApproveGate {
                        gate_id: Some(target_id.clone()),
                        reason: Some(format!("Rejected by {sender} via Telegram")),
                    },
                    true,
                );
                let ok = resp.status == intercom_core::DemarchStatus::Ok;
                (resp.result, if ok { format!("❌ Gate {target_id} rejected by @{sender}") } else { format!("❌ Failed: {}", resp.result) })
            }
            "defer" => {
                // Defer = no kernel action, just acknowledge and remove buttons
                (String::new(), format!("⏸ Gate {target_id} deferred by @{sender}"))
            }
            "extend" => {
                // Budget extension — future: wire to ic budget extend
                (String::new(), format!("📈 Budget extended for run {target_id} by @{sender}"))
            }
            "cancel" => {
                // Run cancellation — future: wire to ic run cancel
                (String::new(), format!("🛑 Run {target_id} cancelled by @{sender}"))
            }
            _ => {
                self.answer_callback_query(&request.callback_query_id, Some("Unknown action"))
                    .await?;
                return Ok(TelegramCallbackResponse {
                    ok: false,
                    action: action.to_string(),
                    target_id,
                    result: None,
                    error: Some(format!("Unknown callback action: {action}")),
                });
            }
        };

        // Edit the original message to show the result (removes buttons)
        let _ = self
            .edit_message(TelegramEditRequest {
                jid: request.chat_jid.clone(),
                message_id: request.message_id.clone(),
                text: status_text.clone(),
            })
            .await;

        // Answer the callback query (dismisses loading spinner)
        self.answer_callback_query(&request.callback_query_id, Some(&status_text))
            .await?;

        Ok(TelegramCallbackResponse {
            ok: true,
            action: action.to_string(),
            target_id,
            result: Some(write_result),
            error: None,
        })
    }
```

**Step 3: Add HTTP route in main.rs**

Find where the other Telegram routes are registered in `main.rs` and add:

```rust
.route("/v1/telegram/callback", post(handle_telegram_callback))
```

Add the handler function:

```rust
async fn handle_telegram_callback(
    State(state): State<AppState>,
    Json(request): Json<telegram::TelegramCallbackRequest>,
) -> impl IntoResponse {
    match state.telegram.handle_callback(request, &state.demarch).await {
        Ok(response) => Json(response).into_response(),
        Err(err) => {
            tracing::error!(error = %err, "Telegram callback handler failed");
            (
                axum::http::StatusCode::INTERNAL_SERVER_ERROR,
                Json(telegram::TelegramCallbackResponse {
                    ok: false,
                    action: String::new(),
                    target_id: String::new(),
                    result: None,
                    error: Some(err.to_string()),
                }),
            )
                .into_response()
        }
    }
}
```

**Step 4: Verify Rust compiles**

Run: `cd apps/intercom && cargo check --manifest-path rust/Cargo.toml --workspace`
Expected: No errors

**Step 5: Commit**

```bash
git add apps/intercom/rust/intercomd/src/telegram.rs apps/intercom/rust/intercomd/src/main.rs
git commit -m "feat(intercom): Telegram callback query handler for gate approval and budget actions"
```

---

### Task 7: Wire Telegram callback routing in Node host

**Files:**
- Modify: `apps/intercom/src/channels/telegram.ts`

The Grammy bot library on the Node side receives Telegram webhook updates including `callback_query` events. These need to be forwarded to intercomd's `/v1/telegram/callback` endpoint.

**Step 1: Find the Grammy bot setup and add callback query handler**

In the Telegram channel file, add a callback query handler that forwards to intercomd:

```typescript
bot.on('callback_query:data', async (ctx) => {
  const callbackData = ctx.callbackQuery.data;
  const chatId = ctx.callbackQuery.message?.chat.id;
  const messageId = ctx.callbackQuery.message?.message_id;
  const senderId = ctx.callbackQuery.from.id;
  const senderName = ctx.callbackQuery.from.first_name || ctx.callbackQuery.from.username || 'unknown';

  if (!chatId || !messageId) {
    await ctx.answerCallbackQuery({ text: 'Invalid callback context' });
    return;
  }

  try {
    const response = await intercomdClient.telegramCallback({
      callback_query_id: ctx.callbackQuery.id,
      chat_jid: String(chatId),
      message_id: String(messageId),
      sender_id: String(senderId),
      sender_name: senderName,
      data: callbackData,
    });

    if (!response.ok) {
      await ctx.answerCallbackQuery({ text: response.error || 'Action failed' });
    }
    // intercomd already answered the callback and edited the message
  } catch (err) {
    logger.error({ err, callbackData }, 'Failed to forward callback to intercomd');
    await ctx.answerCallbackQuery({ text: 'Internal error — try again' });
  }
});
```

**Step 2: Add telegramCallback method to intercomd-client.ts**

```typescript
async telegramCallback(request: {
  callback_query_id: string;
  chat_jid: string;
  message_id: string;
  sender_id?: string;
  sender_name?: string;
  data: string;
}): Promise<{ ok: boolean; action: string; target_id: string; result?: string; error?: string }> {
  const response = await fetch(`${this.baseUrl}/v1/telegram/callback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  return response.json();
}
```

**Step 3: Verify TypeScript compiles**

Run: `cd apps/intercom && npx tsc --noEmit`
Expected: No errors

**Step 4: Commit**

```bash
git add apps/intercom/src/channels/telegram.ts apps/intercom/src/intercomd-client.ts
git commit -m "feat(intercom): wire Telegram callback queries to intercomd gate approval handler"
```

---

### Task 8: Add Rust tests for callback handler and button builders

**Files:**
- Modify: `apps/intercom/rust/intercomd/src/telegram.rs` (add test module)
- Modify: `apps/intercom/rust/intercomd/src/events.rs` (update existing tests)

**Step 1: Add unit tests for button builders**

In `events.rs` test module:

```rust
#[test]
fn gate_buttons_have_correct_callback_data() {
    let buttons = gate_approval_buttons("gate-review");
    assert_eq!(buttons.inline_keyboard.len(), 1);
    assert_eq!(buttons.inline_keyboard[0].len(), 3);
    assert_eq!(buttons.inline_keyboard[0][0].callback_data, "approve:gate-review");
    assert_eq!(buttons.inline_keyboard[0][1].callback_data, "reject:gate-review");
    assert_eq!(buttons.inline_keyboard[0][2].callback_data, "defer:gate-review");
}

#[test]
fn budget_buttons_have_correct_callback_data() {
    let buttons = budget_action_buttons("run-abc");
    assert_eq!(buttons.inline_keyboard.len(), 1);
    assert_eq!(buttons.inline_keyboard[0].len(), 2);
    assert_eq!(buttons.inline_keyboard[0][0].callback_data, "extend:run-abc");
    assert_eq!(buttons.inline_keyboard[0][1].callback_data, "cancel:run-abc");
}
```

**Step 2: Add unit tests for callback data parsing**

In `telegram.rs`, add a test module:

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_approve_callback_data() {
        let data = "approve:gate-review";
        let parts: Vec<&str> = data.splitn(2, ':').collect();
        assert_eq!(parts[0], "approve");
        assert_eq!(parts[1], "gate-review");
    }

    #[test]
    fn parses_callback_with_colons_in_id() {
        let data = "approve:gate:with:colons";
        let parts: Vec<&str> = data.splitn(2, ':').collect();
        assert_eq!(parts[0], "approve");
        assert_eq!(parts[1], "gate:with:colons");
    }

    #[test]
    fn rejects_invalid_callback_data() {
        let data = "nocolon";
        let parts: Vec<&str> = data.splitn(2, ':').collect();
        assert_eq!(parts.len(), 1);
    }

    #[test]
    fn inline_keyboard_serializes_correctly() {
        let markup = InlineKeyboardMarkup {
            inline_keyboard: vec![vec![
                InlineKeyboardButton {
                    text: "OK".to_string(),
                    callback_data: "ok:1".to_string(),
                },
            ]],
        };
        let json = serde_json::to_value(&markup).unwrap();
        assert!(json["inline_keyboard"][0][0]["text"].as_str() == Some("OK"));
        assert!(json["inline_keyboard"][0][0]["callback_data"].as_str() == Some("ok:1"));
    }
}
```

**Step 3: Run all tests**

Run: `cd apps/intercom && cargo test --manifest-path rust/Cargo.toml --workspace`
Expected: All tests pass (existing + new)

**Step 4: Commit**

```bash
git add apps/intercom/rust/intercomd/src/telegram.rs apps/intercom/rust/intercomd/src/events.rs
git commit -m "test(intercom): add tests for inline keyboard buttons and callback data parsing"
```

---

### Task 9: Integration test — end-to-end write tool via IPC

**Files:**
- Create: `apps/intercom/container/shared/demarch-tools.test.ts` (if test infrastructure exists)

**Step 1: Test write tools can construct correct IPC queries**

This is a lightweight verification that write functions produce correctly-shaped IPC query files. In a test environment without a real host, verify the queryKernel call shape:

```typescript
import { describe, it, expect, vi } from 'vitest';

// Mock queryKernel to capture calls
vi.mock('./ipc-demarch.js', () => ({
  queryKernel: vi.fn().mockResolvedValue('{"ok":true}'),
}));

import { queryKernel } from './ipc-demarch.js';
import {
  demarchCreateIssue,
  demarchCloseIssue,
  demarchApproveGate,
  demarchResearch,
} from './demarch-tools.js';

describe('demarch write tools', () => {
  it('create_issue sends title and optional params', async () => {
    const ctx = {} as any;
    await demarchCreateIssue(ctx, 'Test issue', 'Description', '2', 'task');
    expect(queryKernel).toHaveBeenCalledWith('create_issue', {
      title: 'Test issue',
      description: 'Description',
      priority: '2',
      issue_type: 'task',
    });
  });

  it('close_issue sends id and optional reason', async () => {
    const ctx = {} as any;
    await demarchCloseIssue(ctx, 'beads-abc', 'done');
    expect(queryKernel).toHaveBeenCalledWith('close_issue', {
      id: 'beads-abc',
      reason: 'done',
    });
  });

  it('approve_gate sends gate_id', async () => {
    const ctx = {} as any;
    await demarchApproveGate(ctx, 'gate-review', 'LGTM');
    expect(queryKernel).toHaveBeenCalledWith('approve_gate', {
      gate_id: 'gate-review',
      reason: 'LGTM',
    });
  });

  it('research sends query', async () => {
    const ctx = {} as any;
    await demarchResearch(ctx, 'WebSocket performance');
    expect(queryKernel).toHaveBeenCalledWith('research', {
      query: 'WebSocket performance',
    });
  });
});
```

**Step 2: Run tests**

Run: `cd apps/intercom && npx vitest run container/shared/demarch-tools.test.ts`
Expected: All tests pass

**Step 3: Commit**

```bash
git add apps/intercom/container/shared/demarch-tools.test.ts
git commit -m "test(intercom): integration tests for Demarch write tools and research tool"
```

---

### Task 10: Build, restart services, and verify

**Files:** None (operational verification)

**Step 1: Build TypeScript**

Run: `cd apps/intercom && npm run build`
Expected: Clean build

**Step 2: Build Rust**

Run: `cd apps/intercom && npm run rust:build:release`
Expected: Clean build

**Step 3: Run full test suites**

Run: `cd apps/intercom && npm test && npm run rust:test`
Expected: All tests pass

**Step 4: Restart services**

Run:
```bash
systemctl --user restart intercomd
systemctl --user restart intercom
```

**Step 5: Verify health endpoints**

Run:
```bash
curl -s http://127.0.0.1:7340/healthz | jq .
curl -s http://127.0.0.1:7340/readyz | jq .
```
Expected: Both return `ok` status

**Step 6: Commit build artifacts (if dist is tracked)**

```bash
git add -A
git commit -m "build(intercom): H2 last mile — write tools, gate approval, research tool"
```
