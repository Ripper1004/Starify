const params = new URLSearchParams(self.location.search)
const scriptName = params.get("script") || "./starify.js"
// the page passes the real .wasm name; guessing it from the script name is only a fallback
const wasmName = params.get("wasm") || scriptName.replace(".js", "_bg.wasm")

try {
  const appModule = await import(scriptName)

  await appModule.default(wasmName)
} catch (e) {
  console.error("worker failed to initialize:", e)
  throw e
}
