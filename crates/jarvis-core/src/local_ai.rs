// Local (offline) LLM fallback for phrases no command/intent matched.
//
// This is the last resort in the routing chain in
// crates/jarvis-app/src/app.rs::execute_command, tried after Claude (if the
// user configured their own key) and after a custom cloud endpoint (if the
// user configured one) both failed or weren't configured. Unlike those, it
// needs no setup and no network - the model ships inside the installer
// (see .github/workflows/build-windows.yml) and is on by default, so a
// fresh install can already hold a short conversation with zero clicks in
// Settings.
//
// Reply-only, same as custom_ai.rs: a 0.5B model has no business guessing
// which Jarvis command to run, that's what the intent classifier and
// fuzzy matcher are for. This only ever answers in plain text.

use crate::config;
use crate::models::{self, loaders::llm};
use crate::DB;

#[derive(Debug, Clone)]
pub enum LocalDecision {
    Reply { text: String },
}

/// True unless the user explicitly disabled the local AI fallback in
/// settings (on by default).
pub fn is_enabled() -> bool {
    DB.get().map(|db| db.read().local_ai_enabled).unwrap_or(config::DEFAULT_LOCAL_AI_ENABLED)
}

/// Ask the bundled local model to answer `phrase` directly. Loads the model
/// on first use (kept warm in the registry afterwards). Returns an error if
/// disabled, not bundled, or generation fails - the caller treats that the
/// same as "nothing matched" (see app.rs).
pub fn ask(phrase: &str) -> Result<LocalDecision, String> {
    if !is_enabled() {
        return Err("local AI is disabled".to_string());
    }

    let model = llm::load(models::registry(), config::LOCAL_AI_MODEL_ID)?;

    let lang = crate::i18n::get_language();
    let system_prompt = format!(
        "You are JARVIS, a small offline voice assistant running locally on the \
        user's PC. Reply with a short, natural, spoken-style answer (no more than \
        1-2 sentences, no markdown, no lists). Reply in the same language the \
        user used (language code: '{lang}'). If you don't know something \
        (e.g. current events, weather, anything requiring internet access), say \
        so briefly instead of guessing.",
        lang = lang
    );

    let text = llm::generate(&model, &system_prompt, phrase, config::LOCAL_AI_MAX_NEW_TOKENS)?;

    if text.is_empty() {
        Err("local model returned an empty response".to_string())
    } else {
        Ok(LocalDecision::Reply { text })
    }
}
