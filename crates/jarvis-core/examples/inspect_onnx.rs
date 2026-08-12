// Throwaway diagnostic: dump a session's input/output tensor names+dtypes+shapes.
// Run with: cargo run --example inspect_onnx -p jarvis-core --features jarvis_app -- <path/to/model.onnx>
fn main() {
    let path = std::env::args().nth(1).expect("usage: inspect_onnx <model.onnx>");
    let session = ort::session::Session::builder()
        .unwrap()
        .commit_from_file(&path)
        .unwrap();

    println!("=== INPUTS ===");
    for outlet in session.inputs() {
        println!("{}: {:?}", outlet.name(), outlet.dtype());
    }
    println!("=== OUTPUTS ===");
    for outlet in session.outputs() {
        println!("{}: {:?}", outlet.name(), outlet.dtype());
    }
}
