from playwright.sync_api import sync_playwright
import logging

class BrowserManager:
    def __init__(self, port=9222):
        self.port = port
        self.playwright = None
        self.browser = None
        self.context = None
        
    def connect(self):
        try:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{self.port}", timeout=10000)
            self.context = self.browser.contexts[0]
            logging.info("Connected to Chrome instance successfully.")
            return True
        except Exception as e:
            logging.error(f"Failed to connect to Chrome: {e}")
            return False
            
    def get_current_page(self):
        if self.context and self.context.pages:
            for page in self.context.pages:
                if 'learn.eltngl.com' in page.url:
                    return page
            return self.context.pages[0]
        return None
        
    def close(self):
        if self.browser:
            try:
                self.browser.close()
            except Exception:
                pass
        if self.playwright:
            try:
                self.playwright.stop()
            except Exception:
                pass
