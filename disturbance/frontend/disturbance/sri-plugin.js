//NOTE: this works over a json manifest for now, likely this will change
import fs from "fs";
import path from "path";
import { normaliseSriManifest } from "./normalise-sri.js";

export default function sriFromManifest({
  manifestPath,
  distDir
}) {
  console.log("sriFromManifest")
  const rawManifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
  const sriMap = normaliseSriManifest(
    rawManifest,
    path.resolve(distDir)
  );

  return {
    name: "vite-sri-from-fs",

    apply: "build",

    transformIndexHtml(html) {
      return html.replace(
        /<(script|link)([^>]+)(src|href)="([^"]+)"([^>]*)>/g,
        (match, tag, before, attr, url, after) => {
          console.log(url)
          const sri = sriMap[url];
          console.log(sri)
          if (!sri) return match;
          return tag === "script"
            ? `<script${before}${attr}="${url}" integrity="${sri}" crossorigin="anonymous"${after}>`
            : `<link${before}${attr}="${url}" integrity="${sri}" crossorigin="anonymous"${after}>`;
        }
      );
    }
  };
}
