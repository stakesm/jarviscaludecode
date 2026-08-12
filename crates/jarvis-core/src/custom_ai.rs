// Custom OpenAI-compatible cloud endpoint integration.
//
// Same purpose as ai.rs (Claude), but for an arbitrary user-supplied
// OpenAI-compatible chat-completions endpoint (base URL + API key + model
// name, all entered by the user in Settings and stored only in their local
// config - never bundled or committed anywhere). This exists because
// third-party/community gateways vary wildly in reliability and don't
// consistently support function/tool calling, so unlike Claude this is
// plain-text-reply only: it never tries to run a Jarvis command directly,
// it just answers. If the endpoint fails (unreachable, out of quota, bad
// response, etc.), the caller falls back to the local model rather than
// giving up - see app.rs::execute_command.

use std::time::Duration;

use serde_json::{json, Value};

use crate::DB;

const REQUEST_TIMEOUT_SECS: u64 = 15;
const MAX_TOKENS: u32 = 200;

#[derive(Debug, Clone)]
pub enum CustomDecision {
    Reply { text: String },
}

/// True if the user has configured both a base URL and an API key for a
/// custom endpoint in settings.
pub fn is_configured() -> bool {
    let Some(db) = DB.get() else { return false };
    let settings = db.read();
    !settings.api_keys.custom_ai_base_url.trim().is_empty()
        && !settings.api_keys.custom_ai_key.trim().is_empty()
}

fn config() -> Option<(String, String, String)> {
    let db = DB.get()?;
    let settings = db.read();
    let base_url = settings.api_keys.custom_ai_base_url.trim().to_string();
    let key = settings.api_keys.custom_ai_key.trim().to_string();
    if base_url.is_empty() || key.is_empty() {
        return None;
    }
    let model = settings.api_keys.custom_ai_model.trim().to_string();
    Some((base_url, key, model))
}

/// Ask the user's custom endpoint to answer `phrase` directly. Returns an
/// error on missing config, network, or API-level failure - callers should
/// fall back to the local model in that case.
pub fn ask(phrase: &str) -> Result<CustomDecision, String> {
    let (base_url, key, model) = config().ok_or_else(|| "custom AI endpoint not configured".to_string())?;
    if model.is_empty() {
        return Err("custom AI endpoint has no model name configured".to_string());
    }

    let lang = crate::i18n::get_language();
    let system_prompt = format!(
        "You are JARVIS, a local voice assistant running on the user's PC. \
        Reply with a short, natural, spoken-style answer (no more than 2-3 \
        sentences, no markdown), in the same language the user used \
        (language code: '{lang}').",
        lang = lang
    );

    let body = json!({
        "model": model,
        "max_tokens": MAX_TOKENS,
        "messages": [
            { "role": "system", "content": system_prompt },
            { "role": "user", "content": phrase }
        ],
    });

    let client = reqwest::blocking::Client::builder()
        .timeout(Duration::from_secs(REQUEST_TIMEOUT_SECS))
        .build()
        .map_err(|e| format!("custom AI client error: {}", e))?;

    let url = format!("{}/chat/completions", base_url.trim_end_matches('/'));

    let response = client
        .post(&url)
        .bearer_auth(&key)
        .header("content-type", "application/json")
        .json(&body)
        .send()
        .map_err(|e| format!("custom AI request failed: {}", e))?;

    let status = response.status();
    let payload: Value = response
        .json()
        .map_err(|e| format!("custom AI response parse error: {}", e))?;

    if !status.is_success() {
        let msg = payload
            .get("error")
            .and_then(|e| e.get("message"))
            .and_then(|m| m.as_str())
            .unwrap_or("unknown error");
        return Err(format!("custom AI error ({}): {}", status, msg));
    }

    let text = payload
        .get("choices")
        .and_then(|c| c.as_array())
        .and_then(|c| c.first())
        .and_then(|c| c.get("message"))
        .and_then(|m| m.get("content"))
        .and_then(|t| t.as_str())
        .unwrap_or("")
        .trim()
        .to_string();

    if text.is_empty() {
        Err("custom AI endpoint returned an empty response".to_string())
    } else {
        Ok(CustomDecision::Reply { text })
    }
}
