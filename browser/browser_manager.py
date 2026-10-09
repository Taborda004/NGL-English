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
            # Pre-activar la pestaña de NGL vía endpoint HTTP de Chrome para desenfocar la omnibox y evitar bloqueos en Chrome 152+
            try:
                import urllib.request, json
                with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/json", timeout=1.5) as r:
                    tabs = json.loads(r.read())
                ngl_tab = next((t for t in tabs if 'eltngl' in t.get('url', '')), None)
                if ngl_tab:
                    req = urllib.request.Request(f"http://127.0.0.1:{self.port}/json/activate/{ngl_tab['id']}")
                    urllib.request.urlopen(req, timeout=1.5)
            except Exception:
                pass

            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.connect_over_cdp(f"http://localhost:{self.port}", timeout=10000)
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
