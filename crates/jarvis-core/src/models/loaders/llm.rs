// Small local LLM (Qwen2.5-0.5B-Instruct, int8-quantized ONNX export) used
// as an offline fallback for free-form replies when no command/intent
// matched and no cloud AI is configured - see local_ai.rs for the caller.
//
// This is a hand-rolled autoregressive decode loop over a raw
// `ort::session::Session`, not `fastembed` (that's pooling/embedding-only)
// and not a new ML backend - same `ort` crate already used by GLiNER
// (models/loaders/gliner.rs) and the embedding classifier.
//
// The bundled ONNX graph (from onnx-community/Qwen2.5-0.5B-Instruct,
// "model_quantized.onnx") takes an explicit key/value cache in and out on
// every call - confirmed by inspecting the graph directly (see the
// throwaway `examples/inspect_onnx.rs` used while building this):
//
//   in:  input_ids            Int64   [batch, seq_len]
//        attention_mask       Int64   [batch, past_len + seq_len]
//        position_ids         Int64   [batch, seq_len]
//        past_key_values.N.key/value  Float32  [batch, 2, past_len, 64]   (N = 0..23)
//   out: logits                Float32 [batch, seq_len, 151936]
//        present.N.key/value  Float32  [batch, 2, past_len + seq_len, 64]
//
// IMPORTANT: despite `input_ids`/`seq_len` nominally allowing more than one
// token per call, this particular export only computes correctly with
// seq_len=1 on *every* call, prefill included - the graph's own symbolic
// shape for attention_mask is literally "past_sequence_length + 1", not
// "+ seq_len". Feeding the whole prompt in one batched call still runs
// without error, but silently produces garbage (the model ends up echoing
// the prompt back instead of replying) - it took a fair bit of isolated
// testing to track that down, so: don't "optimize" this into a batched
// prefill without re-verifying against the graph directly.
//
// Architecture constants below (layer count, KV head count, head dim, EOS
// token) come straight from the model's own config.json (Qwen2.5-0.5B:
// num_hidden_layers=24, num_key_value_heads=2, hidden_size/num_attention_heads=64,
// eos_token_id=151645) - hardcoded rather than parsed at runtime since this
// loader is written for this one bundled model, not a generic loader.

use std::collections::VecDeque;
use std::sync::Arc;
use parking_lot::Mutex;
use ndarray::{Array2, Array4};
use ort::value::Tensor;
use tokenizers::Tokenizer;

use crate::models::registry::ModelRegistry;

const NUM_LAYERS: usize = 24;
const NUM_KV_HEADS: usize = 2;
const HEAD_DIM: usize = 64;
const EOS_TOKEN_ID: i64 = 151645; // <|im_end|>

pub struct LlmModel {
    pub session: Mutex<ort::session::Session>,
    pub tokenizer: Tokenizer,
}

unsafe impl Send for LlmModel {}
unsafe impl Sync for LlmModel {}

pub fn load(registry: &ModelRegistry, model_id: &str) -> Result<Arc<LlmModel>, String> {
    registry.get_or_load::<LlmModel>(model_id, |def| {
        let model_dir = &def.path;
        let model_path = model_dir.join("onnx").join("model_quantized.onnx");
        let tokenizer_path = model_dir.join("tokenizer.json");

        info!("Loading local LLM from: {}", model_dir.display());

        let session = ort::session::Session::builder()
            .map_err(|e| format!("Failed to create ORT session builder: {}", e))?
            .commit_from_file(&model_path)
            .map_err(|e| format!("Failed to load ONNX model: {}", e))?;

        let tokenizer = Tokenizer::from_file(&tokenizer_path)
            .map_err(|e| format!("Failed to load tokenizer: {}", e))?;

        info!("Local LLM loaded: {}", def.name);
        Ok(LlmModel { session: Mutex::new(session), tokenizer })
    })
}

/// Format a system+user turn using Qwen's ChatML template and greedily
/// generate up to `max_new_tokens` reply tokens, stopping early on EOS.
pub fn generate(model: &LlmModel, system_prompt: &str, user_prompt: &str, max_new_tokens: usize) -> Result<String, String> {
    let prompt = format!(
        "<|im_start|>system\n{system}<|im_end|>\n<|im_start|>user\n{user}<|im_end|>\n<|im_start|>assistant\n",
        system = system_prompt,
        user = user_prompt,
    );

    let encoding = model.tokenizer.encode(prompt, false)
        .map_err(|e| format!("tokenizer encode error: {}", e))?;
    let prompt_ids: Vec<i64> = encoding.get_ids().iter().map(|&id| id as i64).collect();
    let prompt_len = prompt_ids.len();
    if prompt_ids.is_empty() {
        return Err("empty prompt after tokenization".to_string());
    }

    let mut session = model.session.lock();

    // KV cache, starts empty (past_len=0 per layer) for the first step
    let mut past_kv: Vec<(Array4<f32>, Array4<f32>)> = (0..NUM_LAYERS)
        .map(|_| (
            Array4::zeros((1, NUM_KV_HEADS, 0, HEAD_DIM)),
            Array4::zeros((1, NUM_KV_HEADS, 0, HEAD_DIM)),
        ))
        .collect();

    // one token in, one token out, every call - see the module doc comment
    // for why the prompt can't be batched in as a single multi-token call.
    let mut queue: VecDeque<i64> = prompt_ids.into_iter().collect();
    let mut past_len: usize = 0;
    let mut generated: Vec<i64> = Vec::with_capacity(max_new_tokens);

    // prompt_len calls to walk through the prompt (teacher-forced, discarding
    // the model's own guess at each position) + up to max_new_tokens more to
    // actually generate a reply.
    for step_idx in 0..(prompt_len + max_new_tokens) {
        let token = queue.pop_front().expect("generation queue emptied early");
        let is_prefill_step = step_idx < prompt_len - 1;

        let input_ids_arr = Array2::from_shape_vec((1, 1), vec![token])
            .map_err(|e| format!("input_ids shape error: {}", e))?;
        let attention_mask_arr = Array2::from_elem((1, past_len + 1), 1i64);
        let position_ids_arr = Array2::from_shape_vec((1, 1), vec![past_len as i64])
            .map_err(|e| format!("position_ids shape error: {}", e))?;

        let mut inputs: Vec<(String, ort::session::input::SessionInputValue)> = vec![
            ("input_ids".to_string(), Tensor::from_array(input_ids_arr).map_err(|e| format!("tensor: {}", e))?.into()),
            ("attention_mask".to_string(), Tensor::from_array(attention_mask_arr).map_err(|e| format!("tensor: {}", e))?.into()),
            ("position_ids".to_string(), Tensor::from_array(position_ids_arr).map_err(|e| format!("tensor: {}", e))?.into()),
        ];
        for (i, (k, v)) in past_kv.iter().enumerate() {
            inputs.push((format!("past_key_values.{}.key", i), Tensor::from_array(k.clone()).map_err(|e| format!("tensor: {}", e))?.into()));
            inputs.push((format!("past_key_values.{}.value", i), Tensor::from_array(v.clone()).map_err(|e| format!("tensor: {}", e))?.into()));
        }

        let outputs = session.run(inputs).map_err(|e| format!("ort inference error: {}", e))?;

        let (_, logits_data) = outputs["logits"]
            .try_extract_tensor::<f32>()
            .map_err(|e| format!("Failed to extract logits: {}", e))?;

        // greedy decoding - deterministic and cheap, fine for short
        // fallback replies on weak hardware (no sampling/temperature).
        let next_id = logits_data
            .iter()
            .enumerate()
            .max_by(|a, b| a.1.partial_cmp(b.1).unwrap_or(std::cmp::Ordering::Equal))
            .map(|(idx, _)| idx as i64)
            .ok_or("model produced no logits")?;

        // pull the updated cache out of this step's outputs before `outputs`
        // (which borrows `session`) goes out of scope
        for i in 0..NUM_LAYERS {
            let (kshape, kdata) = outputs[format!("present.{}.key", i).as_str()]
                .try_extract_tensor::<f32>()
                .map_err(|e| format!("Failed to extract present.{}.key: {}", i, e))?;
            let (vshape, vdata) = outputs[format!("present.{}.value", i).as_str()]
                .try_extract_tensor::<f32>()
                .map_err(|e| format!("Failed to extract present.{}.value: {}", i, e))?;

            let kdims: Vec<usize> = kshape.iter().map(|&d| d as usize).collect();
            let vdims: Vec<usize> = vshape.iter().map(|&d| d as usize).collect();
            past_kv[i] = (
                Array4::from_shape_vec((kdims[0], kdims[1], kdims[2], kdims[3]), kdata.to_vec())
                    .map_err(|e| format!("present.key reshape error: {}", e))?,
                Array4::from_shape_vec((vdims[0], vdims[1], vdims[2], vdims[3]), vdata.to_vec())
                    .map_err(|e| format!("present.value reshape error: {}", e))?,
            );
        }

        past_len += 1;

        if is_prefill_step {
            // teacher-forcing through the prompt - the model's own guess at
            // this position is discarded, the real next prompt token is
            // already queued.
            continue;
        }

        generated.push(next_id);
        if next_id == EOS_TOKEN_ID || generated.len() >= max_new_tokens {
            break;
        }
        queue.push_back(next_id);
    }

    let ids: Vec<u32> = generated.into_iter()
        .filter(|&id| id != EOS_TOKEN_ID)
        .map(|id| id as u32)
        .collect();

    let text = model.tokenizer.decode(&ids, true)
        .map_err(|e| format!("tokenizer decode error: {}", e))?;

    Ok(text.trim().to_string())
}
