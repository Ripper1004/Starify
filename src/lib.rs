#![warn(clippy::all, rust_2018_idioms)]

mod app;
pub use app::StarifyApp;
#[cfg(not(target_arch = "wasm32"))]
pub use app::generate_preset;
#[cfg(target_arch = "wasm32")]
pub use app::worker_entry;
