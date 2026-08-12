use crate::config;
use serde::{Deserialize, Serialize};

use crate::config::structs::SpeechToTextEngine;
use crate::config::structs::WakeWordEngine;
use crate::config::structs::NoiseSuppressionBackend;

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct Settings {
    pub microphone: i32,
    pub voice: String,

    pub wake_word_engine: WakeWordEngine,

    // backend selections (string IDs matching model or code backend IDs)
    #[serde(default = "default_intent_backend")]
    pub intent_backend: String,
    #[serde(default = "default_slots_backend")]
    pub slots_backend: String,
    #[serde(default = "default_vad_backend")]
    pub vad_backend: String,

    pub gliner_model: String,

    pub speech_to_text_engine: SpeechToTextEngine,
    pub vosk_model: String,

    // audio processing
    pub noise_suppression: NoiseSuppressionBackend,
    pub gain_normalizer: bool,

    // offline fallback LLM for phrases no command/intent matched. bundled
    // with the installer (see local_ai.rs) - on by default, no setup needed.
    #[serde(default = "default_local_ai_enabled")]
    pub local_ai_enabled: bool,

    #[serde(default = "default_language")]
    pub language: String,

    pub api_keys: ApiKeys,

    // Claude (Anthropic) model used to route/answer speech that no local
    // command or intent could handle. See src/ai.rs.
    #[serde(default = "default_claude_model")]
    pub claude_model: String,
}

fn default_intent_backend() -> String { config::DEFAULT_INTENT_BACKEND.to_string() }
fn default_slots_backend() -> String { config::DEFAULT_SLOTS_BACKEND.to_string() }
fn default_vad_backend() -> String { config::DEFAULT_VAD_BACKEND.to_string() }
fn default_language() -> String { crate::i18n::detect_system_language().to_string() }
fn default_claude_model() -> String { "claude-opus-5".to_string() }
fn default_local_ai_enabled() -> bool { config::DEFAULT_LOCAL_AI_ENABLED }

// ### KEY-VALUE ACCESS

impl Settings {
    /// read a setting by key. returns None for unknown keys.
    pub fn get(&self, key: &str) -> Option<String> {
        match key {
            "selected_microphone"       => Some(self.microphone.to_string()),
            "assistant_voice"           => Some(self.voice.clone()),
            "selected_wake_word_engine" => Some(format!("{:?}", self.wake_word_engine)),
            "intent_backend"            => Some(self.intent_backend.clone()),
            "slots_backend"             => Some(self.slots_backend.clone()),
            "vad_backend"               => Some(self.vad_backend.clone()),
            "selected_gliner_model"     => Some(self.gliner_model.clone()),
            "selected_vosk_model"       => Some(self.vosk_model.clone()),
            "speech_to_text_engine"     => Some(format!("{:?}", self.speech_to_text_engine)),
            "noise_suppression"         => Some(format!("{:?}", self.noise_suppression)),
            "gain_normalizer"           => Some(self.gain_normalizer.to_string()),
            "local_ai_enabled"          => Some(self.local_ai_enabled.to_string()),
            "language"                  => Some(self.language.clone()),
            "api_key__picovoice"        => Some(self.api_keys.picovoice.clone()),
            "api_key__openai"           => Some(self.api_keys.openai.clone()),
            "api_key__claude"           => Some(self.api_keys.claude.clone()),
            "claude_model"              => Some(self.claude_model.clone()),
            "custom_ai_base_url"        => Some(self.api_keys.custom_ai_base_url.clone()),
            "custom_ai_key"             => Some(self.api_keys.custom_ai_key.clone()),
            "custom_ai_model"           => Some(self.api_keys.custom_ai_model.clone()),
            _ => None,
        }
    }

    /// write a setting by key. returns Err for unknown keys or invalid values.
    pub fn set(&mut self, key: &str, val: &str) -> Result<(), String> {
        match key {
            "selected_microphone" => {
                self.microphone = val.parse::<i32>()
                    .map_err(|_| format!("invalid integer: '{}'", val))?;
            }
            "assistant_voice" => {
                self.voice = val.to_string();
            }
            "selected_wake_word_engine" => {
                self.wake_word_engine = match val.to_lowercase().as_str() {
                    "rustpotter" => WakeWordEngine::Rustpotter,
                    "vosk"       => WakeWordEngine::Vosk,
                    "porcupine"  => WakeWordEngine::Porcupine,
                    _ => return Err(format!("unknown wake word engine: '{}'", val)),
                };
            }
            "intent_backend" => {
                self.intent_backend = val.to_string();
            }
            "slots_backend" => {
                self.slots_backend = val.to_string();
            }
            "vad_backend" => {
                self.vad_backend = val.to_string();
            }
            "selected_gliner_model" => {
                self.gliner_model = val.to_string();
            }
            "selected_vosk_model" => {
                self.vosk_model = val.to_string();
            }
            "noise_suppression" => {
                self.noise_suppression = match val.to_lowercase().as_str() {
                    "none"        => NoiseSuppressionBackend::None,
                    "nnnoiseless" => NoiseSuppressionBackend::Nnnoiseless,
                    _ => return Err(format!("unknown noise suppression backend: '{}'", val)),
                };
            }
            "gain_normalizer" => {
                self.gain_normalizer = match val.to_lowercase().as_str() {
                    "true"  => true,
                    "false" => false,
                    _ => return Err(format!("expected 'true' or 'false', got: '{}'", val)),
                };
            }
            "local_ai_enabled" => {
                self.local_ai_enabled = match val.to_lowercase().as_str() {
                    "true"  => true,
                    "false" => false,
                    _ => return Err(format!("expected 'true' or 'false', got: '{}'", val)),
                };
            }
            "language" => {
                self.language = val.to_string();
            }
            "api_key__picovoice" => {
                self.api_keys.picovoice = val.to_string();
            }
            "api_key__openai" => {
                self.api_keys.openai = val.to_string();
            }
            "api_key__claude" => {
                self.api_keys.claude = val.to_string();
            }
            "claude_model" => {
                self.claude_model = if val.trim().is_empty() {
                    default_claude_model()
                } else {
                    val.to_string()
                };
            }
            "custom_ai_base_url" => {
                self.api_keys.custom_ai_base_url = val.to_string();
            }
            "custom_ai_key" => {
                self.api_keys.custom_ai_key = val.to_string();
            }
            "custom_ai_model" => {
                self.api_keys.custom_ai_model = val.to_string();
            }
            _ => return Err(format!("unknown setting: '{}'", key)),
        }
        Ok(())
    }

    /// all valid setting keys (for enumeration, debugging, etc.)
    pub fn keys() -> &'static [&'static str] {
        &[
            "selected_microphone",
            "assistant_voice",
            "selected_wake_word_engine",
            "intent_backend",
            "slots_backend",
            "vad_backend",
            "selected_gliner_model",
            "selected_vosk_model",
            "speech_to_text_engine",
            "noise_suppression",
            "gain_normalizer",
            "local_ai_enabled",
            "language",
            "api_key__picovoice",
            "api_key__openai",
            "api_key__claude",
            "claude_model",
            "custom_ai_base_url",
            "custom_ai_key",
            "custom_ai_model",
        ]
    }
}

// ### DEFAULT

impl Default for Settings {
    fn default() -> Settings {
        Settings {
            microphone: -1,
            voice: String::from(""),

            wake_word_engine: config::DEFAULT_WAKE_WORD_ENGINE,

            intent_backend: config::DEFAULT_INTENT_BACKEND.to_string(),
            slots_backend: config::DEFAULT_SLOTS_BACKEND.to_string(),
            vad_backend: config::DEFAULT_VAD_BACKEND.to_string(),

            gliner_model: String::new(),
            speech_to_text_engine: config::DEFAULT_SPEECH_TO_TEXT_ENGINE,
            vosk_model: String::from(""),

            noise_suppression: config::DEFAULT_NOISE_SUPPRESSION,
            gain_normalizer: config::DEFAULT_GAIN_NORMALIZER,
            local_ai_enabled: config::DEFAULT_LOCAL_AI_ENABLED,

            language: crate::i18n::detect_system_language().to_string(),

            api_keys: ApiKeys {
                picovoice: String::from(""),
                openai: String::from(""),
                claude: String::from(""),
                custom_ai_base_url: String::from(""),
                custom_ai_key: String::from(""),
                custom_ai_model: String::from(""),
            },

            claude_model: default_claude_model(),
        }
    }
}

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct ApiKeys {
    pub picovoice: String,
    pub openai: String,
    #[serde(default)]
    pub claude: String,

    // user's own OpenAI-compatible endpoint (see custom_ai.rs) - all empty
    // by default, never bundled/committed, only ever stored in the user's
    // local settings file.
    #[serde(default)]
    pub custom_ai_base_url: String,
    #[serde(default)]
    pub custom_ai_key: String,
    #[serde(default)]
    pub custom_ai_model: String,
}
