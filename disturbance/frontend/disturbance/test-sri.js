
import sriFromManifest from "./sri-plugin.js";

// Simulate Vite input
const plugin = sriFromManifest({
    manifestPath: "/data/data/projects/apiary/sri-manifest.json",
    distDir: "/data/data/projects/apiary/disturbance/"
});

// Fake HTML input (what Vite would pass in)
const html = `
<!DOCTYPE html>
<html>
<head>
  <link rel="stylesheet" href="/static/disturbance_vue/assets/main-8kuMCkKS.css">
</head>
<body>
  <script src="/static/disturbance_vue/assets/main-CNqcm8wq.js"></script>
</body>
</html>
`;

// Call the Vite hook manually
const result = plugin.transformIndexHtml(html);

console.log("=== OUTPUT HTML ===");
console.log(result);
