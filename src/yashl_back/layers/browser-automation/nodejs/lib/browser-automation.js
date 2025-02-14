import chromium from '@sparticuz/chromium-min';
import fsPromises from "fs/promises";
import puppeteer from 'puppeteer-core';

const COMMON_USER_AGENTS = {
  desktop: {
    chrome: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    firefox: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0',
    safari: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
    edge: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.2365.92'
  },
  mobile: {
    chrome: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_3_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/122.0.6261.89 Mobile/15E148 Safari/604.1',
    safari: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_3_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1'
  }
};


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
      headers: null,
      userAgent: { type: 'desktop', browser: 'chrome' }
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

    if (config.userAgent) {
      await this.setUserAgent(config.userAgent);
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

  async takeScreenshot(url, options = {}) {
    const defaultOptions = {
      type: 'png',
      fullPage: false,
      clip: null
    };

    const config = { ...defaultOptions, ...options };
    try {
      await this.page.goto(url);
      console.log('Taking screenshot');
      const screenshot = await this.page.screenshot(config);
      this.browser.close().catch(err => console.error('Error closing browser:', err));
      return screenshot;
    } catch (error) {
      throw new Error(`Screenshot failed: ${error.message}`);
    }
  }

  async setUserAgent(options = {}) {
    const defaultOptions = {
      type: 'desktop',
      browser: 'chrome',
      custom: null
    };

    const config = { ...defaultOptions, ...options };

    try {
      let userAgent;
      
      if (config.custom) {
        userAgent = config.custom;
      } else {
        userAgent = COMMON_USER_AGENTS[config.type]?.[config.browser];
        if (!userAgent) {
          throw new Error(`Invalid user agent configuration: type=${config.type}, browser=${config.browser}`);
        }
      }

      await this.page.setUserAgent(userAgent);
      
      await this.page.evaluateOnNewDocument(() => {
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        Object.defineProperty(navigator, 'plugins', { 
          get: () => [
            {
              description: "Portable Document Format",
              filename: "internal-pdf-viewer",
              name: "Chrome PDF Plugin",
              MimeTypes: [{ type: "application/pdf" }]
            }
          ] 
        });
        
        Object.defineProperty(navigator, 'languages', {
          get: () => ['en-US', 'en']
        });
      });

      console.log(`User agent set to: ${userAgent}`);
    } catch (error) {
      console.error('Error setting user agent:', error);
      throw error;
    }
  }
}
