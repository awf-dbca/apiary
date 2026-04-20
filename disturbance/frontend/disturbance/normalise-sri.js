import path from "path";

export function normaliseSriManifest(rawManifest, distDir) {
  console.log("normaliseSriManifest")
  console.log(distDir)
  const urlManifest = {};

  for (const [fsPath, sri] of Object.entries(rawManifest)) {
    const relative = path.relative(distDir, fsPath);

    if (relative.startsWith("..")) continue;

    const urlPath = "/" + relative.split(path.sep).join("/");
    urlManifest[urlPath] = sri;
    console.log(urlPath, sri)
  }

  return urlManifest;
}
