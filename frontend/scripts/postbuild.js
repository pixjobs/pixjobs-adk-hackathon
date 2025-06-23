const fs = require("fs-extra");
const path = require("path");

async function copyFiles() {
  const projectRoot = path.resolve(__dirname, "..");
  const standaloneDir = path.join(projectRoot, ".next/standalone");
  const staticDir = path.join(projectRoot, ".next/static");
  const publicDir = path.join(projectRoot, "public");

  // Define target directories
  const targetStaticDir = path.join(standaloneDir, ".next/static");
  const targetPublicDir = path.join(standaloneDir, "public");

  try {
    console.log("Ensuring standalone directory exists...");
    await fs.ensureDir(standaloneDir);

    // Copy static files
    if (await fs.pathExists(staticDir)) {
      console.log(`Copying static files from ${staticDir} to ${targetStaticDir}...`);
      await fs.copy(staticDir, targetStaticDir);
      console.log("Static files copied successfully!");
    } else {
      console.warn(`Static directory "${staticDir}" does not exist. Skipping.`);
    }

    // Copy public files
    if (await fs.pathExists(publicDir)) {
      console.log(`Copying public files from ${publicDir} to ${targetPublicDir}...`);
      await fs.copy(publicDir, targetPublicDir);
      console.log("Public files copied successfully!");
    } else {
      console.warn(`Public directory "${publicDir}" does not exist. Skipping.`);
    }
  } catch (error) {
    console.error("Error during post-build file copying:", error);
    process.exit(1); // Exit with error code to indicate failure
  }
}

copyFiles();