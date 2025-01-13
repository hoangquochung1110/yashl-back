import chromium from '@sparticuz/chromium-min';
import fsPromises from "fs/promises";
import puppeteer from 'puppeteer-core';


export default class BrowserAutomation {
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
      cookieFilePath: './cookies.json'
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

    await this.loadCookies();

    if (config.headers) {
      await this.page.setExtraHTTPHeaders(config.headers);
    }
    console.log('Browser initialized');
  }

  async loadCookies() {
    try {
      console.log('Loading cookies from:', this.config.cookieFilePath);
      const cookiesData = await fsPromises.readFile(this.config.cookieFilePath, 'utf8');
      const cookies = JSON.parse(cookiesData);
      await this.browser.setCookie(...cookies);
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
      authStrategy: 'none',
      credentials: {
        username: null,
        password: null,
        selectors: {
          username: 'input[name=email]',
          password: 'input[name=password]',
          submit: 'button[type=submit]'
        }
      },
      waitForSelector: null,
      beforeScreenshot: null
    };

    const config = { ...defaultOptions, ...options };

    await this.page.goto(url, {
      waitUntil: config.waitUntil,
      timeout: config.timeout
    });

    await this.handleAuth(config.authStrategy, config.credentials);

    if (config.waitForSelector) {
      await this.page.waitForSelector(config.waitForSelector, { timeout: config.timeout });
    }

    if (config.beforeScreenshot && typeof config.beforeScreenshot === 'function') {
      await config.beforeScreenshot(this.page);
    }
  }

  async handleAuth(strategy, credentials) {
    switch (strategy) {
      case 'dismiss':
        await this.dismissDialogs();
        break;
      
      case 'login':
        await this.performLogin(credentials);
        await this.saveCookies(); // Save cookies after login
        break;
      
      case 'auto':
        await this.dismissDialogs();
        const needsLogin = await this.checkLoginRequired(credentials.selectors.username);
        if (needsLogin) {
          await this.performLogin(credentials);
          await this.saveCookies(); // Save cookies after login
        }
        break;

      case 'none':
      default:
        break;
    }
  }

  async dismissDialogs() {
    try {
      await this.page.keyboard.press('Escape');
      await this.page.waitForNetworkIdle({concurrency: 2});
    } catch (error) {
      console.warn('Failed to dismiss dialogs:', error.message);
    }
  }

  async checkLoginRequired(usernameSelector) {
    try {
      console.log("Check if there's login form with selector: ", usernameSelector)
      const loginForm = await this.page.$(usernameSelector);
      return loginForm !== null;
    } catch (error) {
      console.warn('Failed to check login status:', error.message);
      return false;
    }
  }

  async performLogin(credentials) {
    if (!credentials.username || !credentials.password) {
      throw new Error('Credentials required for login strategy');
    }

    try {
      const { username, password, selectors } = credentials;

      await this.page.waitForSelector(selectors.username);
      await this.page.type(selectors.username, username);
      await this.page.type(selectors.password, password);

      await Promise.all([
        this.page.waitForNavigation({ waitUntil: 'networkidle2' }),
        this.page.click(selectors.submit)
      ]);

    } catch (error) {
      throw new Error(`Login failed: ${error.message}`);
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
      return screenshot;
    } catch (error) {
      throw new Error(`Screenshot failed: ${error.message}`);
    } finally {
      await this.browser.close().catch(err => console.error('Error closing browser:', err));
    }
  }
}