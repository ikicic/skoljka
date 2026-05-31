import { build, context } from "esbuild";
import { cpSync, existsSync, mkdirSync } from "fs";

const isWatch = process.argv.includes("--watch");
const isProduction = process.argv.includes("--production");

// Copy vendor files from node_modules into static/vendor/
mkdirSync("static/vendor/htmx", { recursive: true });
mkdirSync("static/vendor/katex", { recursive: true });

cpSync("node_modules/htmx.org/dist/htmx.min.js", "static/vendor/htmx/htmx.min.js");
cpSync("node_modules/katex/dist/katex.min.js", "static/vendor/katex/katex.min.js");
cpSync("node_modules/katex/dist/katex.min.css", "static/vendor/katex/katex.min.css");
cpSync("node_modules/katex/dist/fonts", "static/vendor/katex/fonts", { recursive: true });

// PDF.js worker (only if pdfjs-dist is installed)
if (existsSync("node_modules/pdfjs-dist")) {
    mkdirSync("static/vendor/pdfjs", { recursive: true });
    cpSync(
        "node_modules/pdfjs-dist/legacy/build/pdf.worker.min.mjs",
        "static/vendor/pdfjs/pdf.worker.min.mjs",
    );
}

console.log("Vendor files copied.");

// Bundle our browser TypeScript
const entryPoints = ["static/ts/main.ts", "static/ts/list-bulk-edit.tsx"];
if (existsSync("node_modules/pdfjs-dist")) {
    entryPoints.push("static/ts/pdf-import.tsx");
}

const opts = {
    entryPoints,
    bundle: true,
    outdir: "static/js",
    format: "esm",
    target: "es2020",
    sourcemap: !isProduction,
    minify: isProduction,
    jsx: "automatic",
};

const serverOpts = {
    entryPoints: ["ts/server/render-markdown.ts"],
    bundle: true,
    outfile: "scripts/render-markdown.mjs",
    platform: "node",
    format: "esm",
    target: "node20",
    packages: "external",
    // Server subprocess renderers: keep readable; minify only browser + CSS in production.
    minify: false,
};

const latexServerOpts = {
    entryPoints: ["ts/server/render-latex.ts"],
    bundle: true,
    outfile: "scripts/render-latex.mjs",
    platform: "node",
    format: "esm",
    target: "node20",
    packages: "external",
    minify: false,
};

const cssOpts = {
    entryPoints: ["static/css/main.css"],
    outfile: "static/css/main.min.css",
    bundle: true,
    minify: true,
};

if (isWatch) {
    const ctx = await context(opts);
    const serverCtx = await context(serverOpts);
    const latexServerCtx = await context(latexServerOpts);
    await ctx.watch();
    await serverCtx.watch();
    await latexServerCtx.watch();
    console.log("Watching for changes...");
} else {
    await build(opts);
    await build(serverOpts);
    await build(latexServerOpts);
    if (isProduction) {
        await build(cssOpts);
        console.log("Production build complete (minified JS + CSS).");
    } else {
        console.log("Build complete.");
    }
}
