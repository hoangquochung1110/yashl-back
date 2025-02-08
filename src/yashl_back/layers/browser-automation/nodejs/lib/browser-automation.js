import chromium from '@sparticuz/chromium-min';
import fsPromises from "fs/promises";
import puppeteer from 'puppeteer-core';


export class BrowserAutomation {
  constructor(config = {}) {
    const defaultConfig = {
      isLocal: process.env.AWS_EXECUTION_ENV === undefined,
      browser: {
        executablePath: null,
        headless: true,
        args: [],
        defaultViewport: null,
        devtools: false,
      },
    };

    this.config = this.mergeConfig(defaultConfig, config);
    this.browser = null;
    this.page = null;
  }

  mergeConfig(defaultConfig, userConfig) {
    return {
      ...defaultConfig,
      ...userConfig,
      browser: {
        ...defaultConfig.browser,
        ...(userConfig.browser || {})
      }
    };
  }

  async initialize(options = {}) {
    const defaultOptions = {
      viewport: { width: 1200, height: 800, deviceScaleFactor: 1 },
      mobile: false,
      permissions: [],
      cookies: null,
      headers: null
    };

    const config = { ...defaultOptions, ...options };

    const browserOptions = {
      executablePath: this.config.isLocal 
        ? '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
        : await chromium.executablePath(this.config.browser.executablePath),
      headless: this.config.browser.headless,
      args: this.config.isLocal ? [] : chromium.args,
      defaultViewport: this.config.isLocal ? null : config.viewport,
      devtools: this.config.browser.devtools,
    };

    this.browser = await puppeteer.launch(browserOptions);
    this.page = await this.browser.newPage();
    
    await this.page.setViewport({
      ...config.viewport,
      isMobile: config.mobile,
    });

    if (config.permissions.length > 0) {
      const context = this.browser.defaultBrowserContext();
      await context.overridePermissions(config.permissions.domain, config.permissions.types);
    }

    if (config.cookies) {
      await this.browser.setCookie(...config.cookies);
    }

    if (config.headers) {
      await this.page.setExtraHTTPHeaders(config.headers);
    }
    console.log('Browser initialized');
  }

  async loadCookies() {
    try {
      await this.browser.setCookie(...this.config.cookies);
    } catch (error) {
      console.warn('No cookies found, or failed to load cookies:', error.message);
    }
  }

  async saveCookies() {
    console.log('Saving cookies to:', this.config.cookieFilePath);
    const cookies = await this.browser.cookies();
    await fsPromises.writeFile(this.config.cookieFilePath, JSON.stringify(cookies, null, 2));
  }

  async navigateAndWait(url, options = {}) {
    const defaultOptions = {
      waitUntil: 'networkidle2',
      timeout: 30000,
      waitForSelector: null,
      beforeScreenshot: null
    };

    const config = { ...defaultOptions, ...options };

    await this.page.goto(url, {
      waitUntil: config.waitUntil,
      timeout: config.timeout
    });

    if (config.waitForSelector) {
      await this.page.waitForSelector(config.waitForSelector, { timeout: config.timeout });
    }

    if (config.beforeScreenshot && typeof config.beforeScreenshot === 'function') {
      await config.beforeScreenshot(this.page);
    }
  }

  async takeScreenshot(options = {}) {
    const defaultOptions = {
      type: 'png',
      fullPage: false,
      clip: null
    };

    const config = { ...defaultOptions, ...options };
    try {
      console.log('Taking screenshot');
      const screenshot = await this.page.screenshot(config);
      this.browser.close().catch(err => console.error('Error closing browser:', err));
      return screenshot;
    } catch (error) {
      throw new Error(`Screenshot failed: ${error.message}`);
    }
  }
}
