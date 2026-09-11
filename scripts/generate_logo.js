const fs = require('fs');
const path = require('path');
const { Resvg } = require('@resvg/resvg-js');

function buildLogoSvg() {
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" width="1024" height="1024">
  <defs>
    <clipPath id="squircle-clip">
      <rect x="24" y="24" width="976" height="976" rx="220" />
    </clipPath>

    <linearGradient id="cyan-glow" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#00f5ff"/>
      <stop offset="100%" stop-color="#0284c7"/>
    </linearGradient>

    <linearGradient id="cyan-soft" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#38bdf8"/>
      <stop offset="100%" stop-color="#0369a1"/>
    </linearGradient>

    <linearGradient id="amber-accent" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#fbbf24"/>
      <stop offset="100%" stop-color="#d97706"/>
    </linearGradient>

    <linearGradient id="slate-chest" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#334155"/>
      <stop offset="100%" stop-color="#0f172a"/>
    </linearGradient>

    <filter id="subtle-shadow" x="-10%" y="-10%" width="120%" height="120%">
      <feDropShadow dx="0" dy="16" stdDeviation="20" flood-color="#000000" flood-opacity="0.14" />
    </filter>
  </defs>

  <!-- Luxury White Squircle Container -->
  <rect x="24" y="24" width="976" height="976" rx="220" fill="#ffffff" stroke="#e2e8f0" stroke-width="6" />

  <g clip-path="url(#squircle-clip)">
    <g transform="translate(512, 512)" filter="url(#subtle-shadow)">

      <!-- Hexagonal Architectural Gateway -->
      <polygon points="
        0,-390
        338,-195
        338,195
        0,390
        -338,195
        -338,-195
      " fill="none" stroke="#0f172a" stroke-width="36" stroke-linejoin="round" />

      <!-- Inner Dashed Accent Ring (Acoustic Radar Frame) -->
      <polygon points="
        0,-355
        307,-177
        307,177
        0,355
        -307,177
        -307,-177
      " fill="none" stroke="#00f5ff" stroke-width="4" opacity="0.45" stroke-dasharray="16, 12" />

      <!-- Acoustic Wave Subtle Arc Accents in Gateway Corners -->
      <path d="M -180,-280 A 300 300 0 0 1 180,-280" fill="none" stroke="#00f5ff" stroke-width="3" opacity="0.3" stroke-dasharray="6, 8" />

      <!-- ================================================================= -->
      <!-- ================================================================= -->
      <!-- 1. WATERTIGHT SOLID SILHOUETTE BASE (Obsidian Underlayer)         -->
      <!-- ================================================================= -->
      <path d="
        M 0,-170
        L 75,-210 L 165,-275 L 160,-170 L 225,-90 L 245,10 L 220,130 L 180,230 L 130,295 L 60,335 L 0,345
        L -60,335 L -130,295 L -180,230 L -220,130 L -245,10 L -225,-90 L -160,-170 L -165,-275 L -75,-210
        Z"
        fill="#070a10" stroke="#0f172a" stroke-width="2" stroke-linejoin="round"
      />

      <!-- ================================================================= -->
      <!-- 2. WINGS & BODY LOWER FACETS (Acoustic Stealth Wings)             -->
      <!-- ================================================================= -->
      <!-- Left Outer Wing Panels -->
      <polygon points="-245,10 -220,130 -180,230 -125,160 -150,40" fill="#0d1420" />
      <polygon points="-180,230 -130,295 -60,335 -50,230 -125,160" fill="#080c14" />
      <polygon points="-225,-90 -245,10 -150,40 -130,-40" fill="#141c2b" />

      <!-- Right Outer Wing Panels (Highlight facets) -->
      <polygon points="245,10 220,130 180,230 125,160 150,40" fill="#1b2536" />
      <polygon points="180,230 130,295 60,335 50,230 125,160" fill="#111826" />
      <polygon points="225,-90 245,10 150,40 130,-40" fill="#243246" />

      <!-- Center Tail / Keel -->
      <polygon points="0,345 -60,335 -50,230 0,250" fill="#0a0f18" />
      <polygon points="0,345 60,335 50,230 0,250" fill="#1a2332" />

      <!-- ================================================================= -->
      <!-- 3. CHEST BREASTPLATE (Acoustic Sensor Diamond Matrix)             -->
      <!-- ================================================================= -->
      <!-- Lower Center Diamond -->
      <polygon points="0,150 -50,230 0,250" fill="#151e2b" />
      <polygon points="0,150 50,230 0,250" fill="#2c3c50" />

      <!-- Mid Chest Ribs Left & Right -->
      <polygon points="0,150 -50,230 -125,160 -65,100" fill="#101724" />
      <polygon points="0,150 50,230 125,160 65,100" fill="#36475e" />

      <!-- Upper Chest Center Shield -->
      <polygon points="0,60 -65,100 0,150" fill="#192332" />
      <polygon points="0,60 65,100 0,150" fill="#435670" />

      <!-- Acoustic Center Telemetry Diamond Pip -->
      <polygon points="0,95 -10,108 0,121 10,108" fill="url(#cyan-glow)" />
      <polygon points="0,88 -16,108 0,128 16,108" fill="none" stroke="#00f5ff" stroke-width="2" opacity="0.75" />

      <!-- ================================================================= -->
      <!-- 4. EARS & CROWN CREST (Audio Localization Sensory Tufts)          -->
      <!-- ================================================================= -->
      <!-- Left Ear Horn (Shadow side) -->
      <polygon points="0,-170 -75,-210 -165,-275 -125,-155" fill="#131b28" />
      <polygon points="-165,-275 -160,-170 -125,-155" fill="#0a0f18" />
      <polygon points="-160,-170 -225,-90 -125,-155" fill="#0f1724" />

      <!-- Right Ear Horn (Highlight side) -->
      <polygon points="0,-170 75,-210 165,-275 125,-155" fill="#2d3c50" />
      <polygon points="165,-275 160,-170 125,-155" fill="#1e2a3b" />
      <polygon points="160,-170 225,-90 125,-155" fill="#3b4d66" />

      <!-- Forehead Center Peak -->
      <polygon points="0,-170 -65,-120 0,-80" fill="#162030" />
      <polygon points="0,-170 65,-120 0,-80" fill="#33455e" />

      <!-- Ear Crest Cyan Accents -->
      <polygon points="-165,-275 -145,-240 -168,-235" fill="url(#cyan-glow)" />
      <polygon points="165,-275 145,-240 168,-235" fill="url(#cyan-glow)" />

      <!-- ================================================================= -->
      <!-- 5. FACIAL DISC (Parabolic Acoustic Collector)                     -->
      <!-- ================================================================= -->
      <!-- Left Brow Ridge (Stern, Focused, Alert Angle) -->
      <polygon points="0,-80 -65,-120 -125,-155 -130,-65" fill="#0c121d" />
      <polygon points="0,-80 -130,-65 -75,-40" fill="#182232" />

      <!-- Right Brow Ridge (Highlight) -->
      <polygon points="0,-80 65,-120 125,-155 130,-65" fill="#28374c" />
      <polygon points="0,-80 130,-65 75,-40" fill="#3f526e" />

      <!-- Left Facial Flange -->
      <polygon points="-130,-65 -225,-90 -150,40 -105,30" fill="#0e1522" />
      <polygon points="-150,40 -125,160 -65,100 -70,50" fill="#090e18" />

      <!-- Right Facial Flange -->
      <polygon points="130,-65 225,-90 150,40 105,30" fill="#25344a" />
      <polygon points="150,40 125,160 65,100 70,50" fill="#1b2638" />

      <!-- Inner Cheek Discs (Acoustic Reflectors) -->
      <polygon points="-75,-40 -130,-65 -105,30 -40,15" fill="#1c283a" />
      <polygon points="75,-40 130,-65 105,30 40,15" fill="#384a64" />

      <polygon points="-105,30 -70,50 0,60 -40,15" fill="#141d2a" />
      <polygon points="105,30 70,50 0,60 40,15" fill="#27364b" />

      <!-- ================================================================= -->
      <!-- 6. EYES (Piercing Almond Optics with Upward Predatory Cant)       -->
      <!-- ================================================================= -->
      <!-- Left Eye Dark Socket (Outer: -115, -85, Inner: -32, -42) -->
      <polygon points="-115,-85 -75,-92 -32,-45 -72,-38" fill="#03060c" stroke="#00f5ff" stroke-width="2.5" stroke-opacity="0.8" />
      <!-- Left Eye Electric Cyan Iris -->
      <polygon points="-102,-82 -75,-86 -44,-46 -72,-42" fill="url(#cyan-glow)" />
      <!-- Left Slit Pupil -->
      <polygon points="-78,-78 -68,-78 -68,-50 -78,-50" fill="#020408" />
      <!-- Left Catchlight -->
      <polygon points="-82,-72 -76,-78 -72,-72 -78,-66" fill="#ffffff" opacity="0.95" />

      <!-- Right Eye Dark Socket (Outer: 115, -85, Inner: 32, -42) -->
      <polygon points="115,-85 75,-92 32,-45 72,-38" fill="#03060c" stroke="#00f5ff" stroke-width="2.5" stroke-opacity="0.8" />
      <!-- Right Eye Electric Cyan Iris -->
      <polygon points="102,-82 75,-86 44,-46 72,-42" fill="url(#cyan-glow)" />
      <!-- Right Slit Pupil -->
      <polygon points="78,-78 68,-78 68,-50 78,-50" fill="#020408" />
      <!-- Right Catchlight -->
      <polygon points="74,-72 80,-78 84,-72 78,-66" fill="#ffffff" opacity="0.95" />

      <!-- ================================================================= -->
      <!-- 7. RAPTOR BEAK (Sleek Geometric Prism with Amber Accent)          -->
      <!-- ================================================================= -->
      <!-- Center Bridge Ridge -->
      <polygon points="0,-80 -25,-10 0,60" fill="#080c14" />
      <polygon points="0,-80 25,-10 0,60" fill="#162030" />

      <!-- Lower Beak Hook with Amber Gleam -->
      <polygon points="0,60 -13,20 -4,-5 0,-5" fill="url(#amber-accent)" opacity="0.9" />
      <polygon points="0,60 13,20 4,-5 0,-5" fill="#fbbf24" opacity="0.95" />
      <polygon points="0,60 -6,45 0,68" fill="#78350f" />
      <polygon points="0,60 6,45 0,68" fill="#b45309" />

      <!-- Center Beak Seam -->
      <line x1="0" y1="-80" x2="0" y2="68" stroke="#020408" stroke-width="2" />

    </g>
  </g>
</svg>`;
}

async function renderLogo() {
  const outputDir = path.resolve(__dirname, '../docs/images');
  const svg = buildLogoSvg();
  const svgPath = path.join(outputDir, 'logo.svg');
  const pngPath = path.join(outputDir, 'logo.png');

  fs.writeFileSync(svgPath, svg, 'utf-8');
  console.log('Saved SVG to:', svgPath);

  const resvg = new Resvg(svg, {
    fitTo: { mode: 'width', value: 1024 },
    font: { loadSystemFonts: false },
  });
  const pngData = resvg.render().asPng();
  fs.writeFileSync(pngPath, pngData);
  console.log('Successfully rendered logo.png at 1024x1024 to:', pngPath);
}

renderLogo().catch(err => {
  console.error('Error rendering logo:', err);
  process.exit(1);
});
