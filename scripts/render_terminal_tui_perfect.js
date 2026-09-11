const fs = require('fs');
const path = require('path');
const { Resvg } = require('@resvg/resvg-js');

// Load the Rich SVG
let svg = fs.readFileSync('docs/images/terminal_tui.svg', 'utf-8');

// Replace Fira Code with standard Windows monospace fonts: Consolas, 'Lucida Console', Courier
svg = svg.replace(/font-family:\s*Fira Code,\s*monospace/g, 'font-family: "Consolas", "Cascadia Code", "Courier New", monospace');
svg = svg.replace(/font-family:\s*arial/g, 'font-family: "Consolas", monospace');

// Ensure system fonts are enabled in resvg
const resvg = new Resvg(svg, {
  fitTo: { mode: 'width', value: 1200 },
  font: {
    loadSystemFonts: true,
    defaultFontFamily: 'Consolas',
  },
});

const png = resvg.render().asPng();
fs.writeFileSync('docs/images/terminal_tui.png', png);
console.log('Successfully re-rendered docs/images/terminal_tui.png with Consolas monospace, size:', png.length);
