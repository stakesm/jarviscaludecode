// Throwaway diagnostic for the local LLM generation loop (models/loaders/llm.rs).
// Run with: cargo run --example gen_test -p jarvis-core --features jarvis_app -- <models_dir> <model_id> <prompt>
use jarvis_core::models::loaders::llm;

fn main() {
    env_logger_init();
    let models_dir = std::env::args().nth(1).expect("usage: gen_test <resources/models dir> <model_id> <prompt>");
    let model_id = std::env::args().nth(2).unwrap_or_else(|| "qwen2.5-0.5b-instruct".to_string());
    let prompt = std::env::args().nth(3).unwrap_or_else(|| "tell me a short joke".to_string());

    // manually build a registry pointing at the given models dir, bypassing APP_DIR
    let registry = jarvis_core::models::ModelRegistry::new();
    let model_dir = std::path::PathBuf::from(&models_dir).join(&model_id);
    registry.set_catalog(vec![jarvis_core::models::ModelDef {
        id: model_id.clone(),
        name: "test".to_string(),
        tasks: vec![jarvis_core::models::Task::Generation],
        description: String::new(),
        path: model_dir,
    }]);

    let model = llm::load(&registry, &model_id).expect("load failed");
    println!("model loaded");

    let system = "You are JARVIS, a helpful voice assistant. Reply briefly in the same language as the user.";
    let text = llm::generate(&model, system, &prompt, 40).expect("generate failed");
    println!("=== REPLY ===\n{}", text);
}

// minimal stderr logger - avoids pulling in a logging backend crate just
// for this throwaway diagnostic
struct StderrLogger;
impl log::Log for StderrLogger {
    fn enabled(&self, _metadata: &log::Metadata) -> bool { true }
    fn log(&self, record: &log::Record) {
        eprintln!("[{}] {}", record.level(), record.args());
    }
    fn flush(&self) {}
}

static LOGGER: StderrLogger = StderrLogger;

fn env_logger_init() {
    log::set_logger(&LOGGER).unwrap();
    log::set_max_level(log::LevelFilter::Debug);
}
