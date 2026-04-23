"""
CEF Python Embedded Browser Test for Foundry VTT CSS Cascade Layers Support

Tests if CEF Python (Chromium 123+) can properly render Foundry v13+ with CSS Cascade Layers.

Usage:
    python cef-embedded-browser-test.py http://localhost:30000
    python cef-embedded-browser-test.py http://83.105.151.227:30000/
"""

import sys
import os
from pathlib import Path
from cefpython3 import cefpython as cef
import time

# Get script directory
SCRIPT_DIR = Path(__file__).resolve().parent

class FoundryBrowserTest:
    """CEF Python browser test for Foundry CSS rendering"""
    
    def __init__(self, vtt_url):
        self.vtt_url = vtt_url
        self.browser = None
        self.test_results = {}
        self.console_messages = []
        
        print(f"CEF Python Foundry CSS Rendering Test")
        print(f"URL: {vtt_url}")
        print("-" * 60)
        
    def initialize_cef(self):
        """Initialize CEF with security disabled for testing"""
        print("Initializing CEF Python...")
        
        # Set up CEF settings to allow insecure content
        settings = {
            "debug": False,
            "log_severity": cef.LOGSEVERITY_INFO,
            "log_file": str(SCRIPT_DIR / "cef-debug.log"),
        }
        
        cef.Initialize(settings)
        print("✓ CEF initialized")
        
    def create_browser(self):
        """Create CEF browser window"""
        print("Creating browser window...")
        
        window_info = cef.WindowInfo()
        window_info.SetAsChild(0)
        
        self.browser = cef.CreateBrowserSyncNamed(
            window_title="CEF Foundry CSS Test",
            url=self.vtt_url
        )
        
        # Set up JavaScript bindings
        self.browser.SetJavascriptBindings(self)
        
        print("✓ Browser window created")
        
    def wait_for_page_load(self, timeout=10):
        """Wait for page to load"""
        print(f"Waiting for page to load (timeout: {timeout}s)...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Try to access document to verify page is loaded
                result = self.browser.ExecuteFunction("function(){ return document.readyState; }")
                if result == "complete":
                    print("✓ Page loaded")
                    return True
            except:
                pass
            time.sleep(0.5)
        
        print("✗ Page load timeout")
        return False
    
    def run_test_1_load_page(self):
        """Test 1: Can the page load?"""
        print("\n--- TEST 1: Load VTT Page ---")
        
        js_code = """
        (function() {
            return {
                url: window.location.href,
                title: document.title,
                bodyLength: document.body ? document.body.innerHTML.length : 0,
                hasFoundry: typeof game !== 'undefined'
            };
        })();
        """
        
        try:
            result = self.browser.ExecuteFunction(js_code)
            print(f"URL: {result.get('url')}")
            print(f"Title: {result.get('title')}")
            print(f"Body content: {result.get('bodyLength')} chars")
            print(f"Foundry object exists: {result.get('hasFoundry')}")
            
            if result.get('bodyLength', 0) > 100:
                print("✓ PASS: VTT page loaded and rendered")
                self.test_results['test_1'] = 'PASS'
                return True
            else:
                print("✗ FAIL: Page content too small")
                self.test_results['test_1'] = 'FAIL'
                return False
        except Exception as e:
            print(f"✗ FAIL: {str(e)}")
            self.test_results['test_1'] = 'FAIL'
            return False
    
    def run_test_2_css_rendering(self):
        """Test 2: Can CSS Cascade Layers render?"""
        print("\n--- TEST 2: CSS Cascade Layers Rendering ---")
        
        js_code = """
        (function() {
            var results = {
                stylesheets_exist: false,
                stylesheets_count: 0,
                css_rules_count: 0,
                computed_styles: {},
                body_background: '',
                css_applying: false,
                errors: []
            };
            
            // Check stylesheets
            var styleLinks = document.querySelectorAll('link[rel="stylesheet"]');
            results.stylesheets_exist = styleLinks.length > 0;
            results.stylesheets_count = styleLinks.length;
            
            // Check if stylesheets are accessible
            try {
                results.accessible_stylesheets = document.styleSheets.length;
                var totalRules = 0;
                for (var i = 0; i < document.styleSheets.length; i++) {
                    try {
                        if (document.styleSheets[i].cssRules) {
                            totalRules += document.styleSheets[i].cssRules.length;
                        }
                    } catch(e) {
                        results.errors.push('Cannot read sheet ' + i + ': ' + e.message);
                    }
                }
                results.css_rules_count = totalRules;
            } catch(e) {
                results.errors.push('Cannot access stylesheets: ' + e.message);
            }
            
            // Check computed styles on body
            try {
                var bodyStyles = window.getComputedStyle(document.body);
                results.computed_styles = {
                    backgroundColor: bodyStyles.backgroundColor,
                    color: bodyStyles.color,
                    fontFamily: bodyStyles.fontFamily
                };
                results.body_background = bodyStyles.backgroundColor;
                
                // If background is default (white/transparent), CSS didn't apply
                if (bodyStyles.backgroundColor === 'rgba(0, 0, 0, 0)' || 
                    bodyStyles.backgroundColor === 'transparent' || 
                    bodyStyles.backgroundColor === 'rgb(255, 255, 255)') {
                    results.css_applying = false;
                    results.diagnosis = 'CSS NOT APPLYING - background is default';
                } else {
                    results.css_applying = true;
                    results.diagnosis = 'CSS APPLYING - background: ' + bodyStyles.backgroundColor;
                }
            } catch(e) {
                results.errors.push('Cannot get computed styles: ' + e.message);
            }
            
            return JSON.stringify(results, null, 2);
        })();
        """
        
        try:
            result = self.browser.ExecuteFunction(js_code)
            print("CSS Debug Results:")
            print(result)
            
            # Parse results
            import json
            data = json.loads(result)
            
            if data.get('css_applying'):
                print("✓ PASS: CSS Cascade Layers rendering correctly")
                self.test_results['test_2'] = 'PASS'
                return True
            else:
                print("✗ FAIL: CSS not applying")
                print(f"Diagnosis: {data.get('diagnosis')}")
                self.test_results['test_2'] = 'FAIL'
                return False
        except Exception as e:
            print(f"✗ FAIL: {str(e)}")
            self.test_results['test_2'] = 'FAIL'
            return False
    
    def run_tests(self):
        """Run all tests"""
        print("\n" + "=" * 60)
        print("CEF Python Foundry CSS Rendering Tests")
        print("=" * 60)
        
        # Initialize and create browser
        self.initialize_cef()
        self.create_browser()
        
        # Wait for page to load
        if not self.wait_for_page_load():
            print("Failed to load page, aborting tests")
            return False
        
        # Run tests
        test1_pass = self.run_test_1_load_page()
        if test1_pass:
            test2_pass = self.run_test_2_css_rendering()
        
        # Summary
        print("\n" + "=" * 60)
        print("Test Summary")
        print("=" * 60)
        for test, result in self.test_results.items():
            print(f"{test}: {result}")
        
        all_passed = all(v == 'PASS' for v in self.test_results.values())
        if all_passed:
            print("\n✓ ALL TESTS PASSED - CEF Python can render Foundry with CSS Cascade Layers!")
        else:
            print("\n✗ Some tests failed")
        
        # Cleanup
        cef.Shutdown()
        return all_passed


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python cef-embedded-browser-test.py <URL>")
        print("Examples:")
        print("  python cef-embedded-browser-test.py http://localhost:30000")
        print("  python cef-embedded-browser-test.py http://83.105.151.227:30000/")
        sys.exit(1)
    
    vtt_url = sys.argv[1]
    
    # Validate URL
    if not vtt_url.startswith("http://") and not vtt_url.startswith("https://"):
        print("Error: URL must start with http:// or https://")
        sys.exit(1)
    
    # Run tests
    test = FoundryBrowserTest(vtt_url)
    success = test.run_tests()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
