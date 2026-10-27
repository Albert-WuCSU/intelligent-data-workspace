import { defineConfig } from './apps/web/node_modules/@playwright/test/index.mjs';
export default defineConfig({testDir:'./tests',testMatch:'*.spec.mjs',workers:1,retries:0,reporter:'list',
  use:{channel:process.env.PLAYWRIGHT_EXECUTABLE_PATH?undefined:'chrome',headless:true,
    launchOptions:process.env.PLAYWRIGHT_EXECUTABLE_PATH?{executablePath:process.env.PLAYWRIGHT_EXECUTABLE_PATH}:{},
    viewport:{width:1440,height:1100}},outputDir:'tmp/m01-browser-results'});
