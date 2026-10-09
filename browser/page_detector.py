class PageDetector:
    def __init__(self, page):
        self.page = page
        
    def is_assignment_page(self):
        if not self.page:
            return False
        if 'learn.eltngl.com' not in self.page.url:
            return False
        return True
        
    def get_assignment_info(self):
        if not self.page:
            return {"title": "No page connected", "unit": "-", "exercise": "-"}
            
        try:
            title = self.page.title()
            # In a real scenario we'd query the DOM for unit/exercise specifics
            return {"title": title, "unit": "Detected Unit", "exercise": "Current"}
        except:
            return {"title": "Unknown", "unit": "Unknown", "exercise": "Unknown"}
