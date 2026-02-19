const fs = require("fs");
const path = require("path");

const src = path.join(__dirname, "..", "encrypted", "index.source.html");
const dest = path.join(__dirname, "..", "index.html");

if (!fs.existsSync(src)) {
  console.error(`Encrypted output not found: ${src}`);
  console.error(`Run: npm run encrypt (with STATICRYPT_PASSWORD set)`);
  process.exit(1);
}

fs.copyFileSync(src, dest);
console.log(`Updated ${dest} from ${src}`);
