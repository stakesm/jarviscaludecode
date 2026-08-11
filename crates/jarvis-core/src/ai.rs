// Claude (Anthropic) integration.
//
// When the local intent classifier and the fuzzy phrase matcher both fail to
// resolve what the user said to a known command, Jarvis can hand the phrase
// to Claude. Every loaded command is exposed to Claude as a tool - if Claude
// decides one of them matches, it calls that tool and Jarvis runs the command
// exactly as if it had been matched locally. If nothing matches (small talk,
// a question, anything outside the command set), Claude answers in plain
// text instead, and that text is surfaced to the user via IPC.
//
// This is plain `reqwest::blocking` HTTP against the Messages API - there is
// no official Anthropic SDK for Rust.

use std::collections::HashMap;
use std::time::Duration;

use serde_json::{json, Value};

use crate::commands::JCommandsList;
use crate::DB;

const API_URL: &str = "https://api.anthropic.com/v1/messages";
const ANTHROPIC_VERSION: &str = "2023-06-01";
const ANTHROPIC_DEFAULT_MODEL: &str = "claude-opus-5";
const REQUEST_TIMEOUT_SECS: u64 = 20;
// generous headroom: on Claude Opus 5, thinking is on by default and shares
// this budget with the actual reply/tool call - too tight and responses
// truncate mid-thought. `effort: "low"` (below) keeps it fast and cheap.
const MAX_TOKENS: u32 = 2048;

// Anthropic caps a request at 128 tool definitions.
const MAX_TOOLS: usize = 128;

#[derive(Debug, Clone)]
pub enum ClaudeDecision {
    /// Claude matched the phrase to one of Jarvis's own commands.
    RunCommand { id: String },
    /// Claude found no matching command and answered directly.
    Reply { text: String },
}

/// True if a Claude API key has been configured in settings.
pub fn is_configured() -> bool {
    api_key().map(|k| !k.trim().is_empty()).unwrap_or(false)
}

fn api_key() -> Option<String> {
    DB.get().map(|db| db.read().api_keys.claude.clone())
}

fn model() -> String {
    DB.get()
        .map(|db| db.read().claude_model.clone())
        .filter(|m| !m.trim().is_empty())
        .unwrap_or_else(|| ANTHROPIC_DEFAULT_MODEL.to_string())
}

/// Ask Claude to either run one of the known Jarvis commands for `phrase`,
/// or answer it directly. Returns an error on missing config, network, or
/// API-level failure - callers should fall back to the usual "not found"
/// handling in that case.
pub fn ask(phrase: &str, commands: &[JCommandsList]) -> Result<ClaudeDecision, String> {
    let key = api_key()
        .filter(|k| !k.trim().is_empty())
        .ok_or_else(|| "Claude API key not configured".to_string())?;

    let toolset = build_tools(commands);
    let lang = crate::i18n::get_language();

    let system_prompt = format!(
        "You are JARVIS, a local voice assistant running on the user's PC. \
        The user just said something a phrase-matcher could not resolve to any \
        known command. You are given one tool per command JARVIS is able to run. \
        Call exactly one tool ONLY if the request clearly matches what that command \
        does - never call a tool for a rough or unrelated guess. \
        If nothing matches, or the user is just chatting, asking a question, or \
        making small talk, do not call any tool: reply with a short, natural, spoken-style \
        answer (no more than 2-3 sentences, no markdown), in the same language the user \
        used (language code: '{lang}').",
        lang = lang
    );

    let body = json!({
        "model": model(),
        "max_tokens": MAX_TOKENS,
        // this is a latency-sensitive routing decision, not a hard reasoning
        // task - keep thinking shallow and fast rather than disabling it
        // outright (disabling it can make tool calls leak into plain text).
        "output_config": { "effort": "low" },
        "system": system_prompt,
        "messages": [
            { "role": "user", "content": phrase }
        ],
        "tools": toolset.definitions,
    });

    let client = reqwest::blocking::Client::builder()
        .timeout(Duration::from_secs(REQUEST_TIMEOUT_SECS))
        .build()
        .map_err(|e| format!("Claude client error: {}", e))?;

    let response = client
        .post(API_URL)
        .header("x-api-key", key)
        .header("anthropic-version", ANTHROPIC_VERSION)
        .header("content-type", "application/json")
        .json(&body)
        .send()
        .map_err(|e| format!("Claude request failed: {}", e))?;

    let status = response.status();
    let payload: Value = response
        .json()
        .map_err(|e| format!("Claude response parse error: {}", e))?;

    if !status.is_success() {
        let msg = payload
            .get("error")
            .and_then(|e| e.get("message"))
            .and_then(|m| m.as_str())
            .unwrap_or("unknown error");
        return Err(format!("Claude API error ({}): {}", status, msg));
    }

    parse_response(&payload, &toolset.id_by_tool_name)
}

struct ToolSet {
    definitions: Vec<Value>,
    // tool name -> original command id (tool names are sanitized, so this
    // map is the source of truth for mapping a tool call back to a command)
    id_by_tool_name: HashMap<String, String>,
}

fn build_tools(commands: &[JCommandsList]) -> ToolSet {
    let lang = crate::i18n::get_language();

    let mut definitions = Vec::new();
    let mut id_by_tool_name = HashMap::new();

    'outer: for list in commands {
        for cmd in &list.commands {
            // "voice" is a marker/no-op type, "stop_chaining" is an internal
            // control command - neither is useful for Claude to invoke directly.
            if matches!(cmd.cmd_type.as_str(), "voice" | "stop_chaining") {
                continue;
            }

            let tool_name = sanitize_tool_name(&cmd.id);

            let mut description = if cmd.description.is_empty() {
                format!("Run the Jarvis command '{}'.", cmd.id)
            } else {
                cmd.description.clone()
            };

            let phrases = cmd.get_phrases(&lang);
            if !phrases.is_empty() {
                description.push_str(" Example phrases the user might say: ");
                description.push_str(
                    &phrases
                        .iter()
                        .take(5)
                        .cloned()
                        .collect::<Vec<_>>()
                        .join("; "),
                );
            }

            definitions.push(json!({
                "name": tool_name.clone(),
                "description": description,
                "input_schema": {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": false
                }
            }));
            id_by_tool_name.insert(tool_name, cmd.id.clone());

            if definitions.len() >= MAX_TOOLS {
                warn!("Claude tool list truncated at {} commands", MAX_TOOLS);
                break 'outer;
            }
        }
    }

    ToolSet { definitions, id_by_tool_name }
}

// Tool names must match ^[a-zA-Z0-9_-]{1,128}$. Command ids are already
// slug-like (from command.toml/yaml), but sanitize defensively and keep the
// name short enough to stay under the limit even for long ids.
fn sanitize_tool_name(command_id: &str) -> String {
    let sanitized: String = command_id
        .chars()
        .map(|c| if c.is_ascii_alphanumeric() || c == '_' || c == '-' { c } else { '_' })
        .take(120)
        .collect();

    format!("run_{}", sanitized)
}

fn parse_response(
    payload: &Value,
    id_by_tool_name: &HashMap<String, String>,
) -> Result<ClaudeDecision, String> {
    let content = payload
        .get("content")
        .and_then(|c| c.as_array())
        .ok_or_else(|| "Claude response missing 'content'".to_string())?;

    // a tool call, if present, always wins over any accompanying text
    for block in content {
        if block.get("type").and_then(|t| t.as_str()) == Some("tool_use") {
            if let Some(name) = block.get("name").and_then(|n| n.as_str()) {
                if let Some(id) = id_by_tool_name.get(name) {
                    return Ok(ClaudeDecision::RunCommand { id: id.clone() });
                }
                warn!("Claude called an unrecognized tool: '{}'", name);
            }
        }
    }

    let text: String = content
        .iter()
        .filter(|b| b.get("type").and_then(|t| t.as_str()) == Some("text"))
        .filter_map(|b| b.get("text").and_then(|t| t.as_str()))
        .collect::<Vec<_>>()
        .join(" ")
        .trim()
        .to_string();

    if text.is_empty() {
        Err("Claude returned an empty response".to_string())
    } else {
        Ok(ClaudeDecision::Reply { text })
    }
}
