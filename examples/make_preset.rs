//! Bakes a bundled preset: morphs an image into the built-in target and writes
//! `presets/<name>/{source.png,assignments.json,output.png}`.
//!
//! cargo run --release --example make_preset -- <image> <name> [--proximity N] [--out DIR]

use std::path::PathBuf;

const SIDELEN: u32 = 128;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut positional = Vec::new();
    let mut proximity: i64 = 5;
    let mut out_dir = PathBuf::from("presets");

    let mut args = std::env::args().skip(1);
    while let Some(arg) = args.next() {
        match arg.as_str() {
            "--proximity" => proximity = args.next().ok_or("--proximity needs a value")?.parse()?,
            "--out" => out_dir = args.next().ok_or("--out needs a value")?.into(),
            _ => positional.push(arg),
        }
    }
    let [image_path, name] = positional.as_slice() else {
        return Err("usage: make_preset <image> <name> [--proximity N] [--out DIR]".into());
    };

    let source = image::open(image_path)?.to_rgb8();
    let (source_pixels, assignments) =
        starify::generate_preset(source, name.clone(), SIDELEN, proximity)?;

    let mut output = vec![0u8; source_pixels.len()];
    for (target_idx, source_idx) in assignments.iter().enumerate() {
        output[target_idx * 3..target_idx * 3 + 3]
            .copy_from_slice(&source_pixels[source_idx * 3..source_idx * 3 + 3]);
    }

    let dir = out_dir.join(name);
    std::fs::create_dir_all(&dir)?;
    image::RgbImage::from_vec(SIDELEN, SIDELEN, source_pixels)
        .ok_or("bad source buffer")?
        .save(dir.join("source.png"))?;
    image::RgbImage::from_vec(SIDELEN, SIDELEN, output)
        .ok_or("bad output buffer")?
        .save(dir.join("output.png"))?;
    let json = assignments
        .iter()
        .map(|a| a.to_string())
        .collect::<Vec<_>>()
        .join(",");
    std::fs::write(dir.join("assignments.json"), format!("[{json}]"))?;

    println!("wrote {}", dir.display());
    Ok(())
}
