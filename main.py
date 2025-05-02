import requests
from bs4 import BeautifulSoup
import json
import time
import random
import os
from urllib.parse import quote
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class AliExpressScraper:
    def __init__(self, output_dir="scraped_products", use_selenium=True):
        # More comprehensive headers for requests
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0",
            "Referer": "https://www.aliexpress.com/",
        }

        self.base_url = "https://www.aliexpress.com/wholesale?SearchText="
        self.output_dir = output_dir
        self.use_selenium = use_selenium

        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Create subdirectories for images
        self.main_images_dir = os.path.join(output_dir, "main_images")
        self.variant_images_dir = os.path.join(output_dir, "variant_images")

        if not os.path.exists(self.main_images_dir):
            os.makedirs(self.main_images_dir)
        if not os.path.exists(self.variant_images_dir):
            os.makedirs(self.variant_images_dir)

        # Create a session for maintaining cookies
        self.session = requests.Session()
        self.session.headers.update(self.headers)

        # Setup Selenium if enabled
        if self.use_selenium:
            self.setup_selenium()

    def download_images(self, image_urls, save_dir, prefix):
        """Download images from URLs and save them to disk with improved error handling"""
        for i, url in enumerate(image_urls):
            try:
                # Skip if URL is empty
                if not url:
                    continue

                # Fix protocol-relative URLs
                if url.startswith("//"):
                    url = "https:" + url

                # Skip if not a valid URL
                if not url.startswith("http"):
                    print(f"Skipping invalid image URL: {url}")
                    continue

                # Fix AliExpress image URLs - remove size restrictions and other parameters
                # This is crucial for 2025 AliExpress image URLs
                url = url.split("_")[0]  # Remove size restrictions like _220x220q75
                if ".jpg_" in url or ".png_" in url or ".webp_" in url:
                    url = url.split("_")[0]

                # Remove .avif extension if present (common in 2025 AliExpress)
                if url.endswith(".avif"):
                    url = url[:-5]

                # Ensure URL ends with a valid image extension
                if not any(
                    url.endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp"]
                ):
                    url = url + ".jpg"  # Default to jpg if no extension

                print(f"Attempting to download: {url}")

                # Add delay between image downloads
                time.sleep(random.uniform(1, 3))

                # Make request with headers
                headers = self.headers.copy()
                headers["Referer"] = "https://www.aliexpress.com/"

                # Add additional headers that might help bypass restrictions
                headers["Accept"] = "image/avif,image/webp,image/apng,image/*,*/*;q=0.8"
                headers["Accept-Encoding"] = "gzip, deflate, br"

                # Set a short timeout for image downloads
                response = requests.get(url, headers=headers, stream=True, timeout=30)

                if response.status_code == 200:
                    # Check if response is actually an image
                    content_type = response.headers.get("content-type", "")
                    if not ("image" in content_type.lower()):
                        print(f"Skipping non-image content: {content_type}")
                        continue

                    # Determine file extension
                    if "jpeg" in content_type or "jpg" in content_type:
                        ext = "jpg"
                    elif "png" in content_type:
                        ext = "png"
                    elif "webp" in content_type:
                        ext = "webp"
                    else:
                        ext = "jpg"  # Default to jpg

                    # Save the image
                    image_path = os.path.join(save_dir, f"{prefix}_{i + 1}.{ext}")
                    with open(image_path, "wb") as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:  # Filter out keep-alive chunks
                                f.write(chunk)

                    print(f"Downloaded image: {image_path}")
                else:
                    print(
                        f"Failed to download image, status code: {response.status_code}"
                    )

                    # Try alternate URL format as fallback
                    if (
                        ".jpg_" in url
                        or ".png_" in url
                        or ".webp_" in url
                        or ".avif" in url
                    ):
                        alt_url = url.replace("_220x220q75", "").replace("_.avif", "")
                        print(f"Attempting alternate URL: {alt_url}")

                        response = requests.get(
                            alt_url, headers=headers, stream=True, timeout=30
                        )
                        if response.status_code == 200:
                            # Check if response is actually an image
                            content_type = response.headers.get("content-type", "")
                            if not ("image" in content_type.lower()):
                                print(f"Skipping non-image content: {content_type}")
                                continue

                            # Determine file extension
                            if "jpeg" in content_type or "jpg" in content_type:
                                ext = "jpg"
                            elif "png" in content_type:
                                ext = "png"
                            elif "webp" in content_type:
                                ext = "webp"
                            else:
                                ext = "jpg"  # Default to jpg

                            # Save the image
                            image_path = os.path.join(
                                save_dir, f"{prefix}_{i + 1}.{ext}"
                            )
                            with open(image_path, "wb") as f:
                                for chunk in response.iter_content(chunk_size=8192):
                                    if chunk:
                                        f.write(chunk)

                            print(f"Downloaded image with alternate URL: {image_path}")

            except requests.exceptions.RequestException as e:
                print(f"Network error downloading image {url}: {e}")
            except Exception as e:
                print(f"Error downloading image {url}: {e}")

    def random_sleep(self, min_seconds=2, max_seconds=8):
        """Sleep for a random amount of time to mimic human behavior"""
        time.sleep(random.uniform(min_seconds, max_seconds))

    def close(self):
        """Close the Selenium WebDriver if it exists"""
        if self.use_selenium and hasattr(self, "driver"):
            self.driver.quit()

    def __del__(self):
        """Cleanup when the object is destroyed"""
        self.close()

    def setup_selenium(self):
        """Initialize Selenium WebDriver with enhanced anti-detection measures"""
        options = Options()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--window-size=1920,1080")

        # Add these additional options for better stealth
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        # Fix for WebGL error
        options.add_argument("--disable-webgl")
        options.add_argument("--enable-unsafe-webgpu")
        options.add_argument("--enable-unsafe-swiftshader")

        # Rotate user agents
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
        ]
        options.add_argument(f"user-agent={random.choice(user_agents)}")

        # Disable automation flags
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        # Initialize the driver
        self.driver = webdriver.Chrome(options=options)

        # Additional stealth techniques
        self.driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": """
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
                window.chrome = { runtime: {} };
            """
            },
        )

    def search_products(self, category, subcategory, item, count=2, proxy=None):
        """Search for products in a specific category"""
        search_term = f"{item} {subcategory}"
        encoded_search = quote(search_term)
        search_url = f"{self.base_url}{encoded_search}"

        print(f"Searching for: {search_term}")

        if self.use_selenium:
            return self._search_products_selenium(
                category, subcategory, item, search_url, count
            )
        else:
            return self._search_products_requests(
                category, subcategory, item, search_url, count, proxy
            )

    def _search_products_requests(
        self, category, subcategory, item, search_url, count=2, proxy=None
    ):
        """Search using requests library"""
        proxies = None
        if proxy:
            proxies = {"http": proxy, "https": proxy}

        try:
            response = self.session.get(
                search_url, headers=self.headers, proxies=proxies, timeout=30
            )

            # Check for unusual traffic detection
            if (
                "unusual traffic" in response.text.lower()
                or "captcha" in response.text.lower()
            ):
                print("Unusual traffic detected! Consider using Selenium mode.")
                return []

            soup = BeautifulSoup(response.text, "html.parser")

            # Extract product listings - updated selector based on current AliExpress structure
            product_elements = soup.select(
                ".product-card, .product-snippet, ._3t7zg, .JIIxO, .manhattan--container--1lP57Ag"
            )[:count]
            if not product_elements:
                print("No product elements found. CSS selectors may need updating.")
                return []

            products = []

            for product in product_elements:
                try:
                    # Extract basic product info - updated selectors
                    title_element = product.select_one(
                        ".product-title, .title, ._7doubR, ._18_85, .manhattan--titleText--WccSjUS"
                    )
                    price_element = product.select_one(
                        ".product-price, .price, .jr_kr, .jr_cr span, .manhattan--price--WvaUgDY"
                    )
                    link_element = product.select_one(
                        'a.product-item, a[href*="/item/"], .manhattan--container--1lP57Ag a'
                    )

                    if title_element and price_element and link_element:
                        href = link_element["href"]
                        print("Raw href:", href)

                        # Fix URL formatting
                        if href.startswith("//"):
                            product_url = f"https:{href}"
                        elif href.startswith("/"):
                            product_url = f"https://aliexpress.com{href}"
                        elif href.startswith("http"):
                            product_url = href
                        else:
                            product_url = f"https://aliexpress.com/{href}"

                        # Clean up double slashes that aren't part of protocol
                        if "//" in product_url[8:]:  # Skip the https:// part
                            product_url = product_url.replace("//", "/", 1)

                        print("Cleaned product URL:", product_url)
                        product_data = self.extract_product_details(product_url)

                        # Add category information
                        product_data["category"] = category
                        product_data["subcategory"] = subcategory
                        product_data["item_type"] = item

                        products.append(product_data)

                        # Save product to disk
                        self.save_product(product_data)

                        # Delay to avoid rate limiting - increased delay
                        time.sleep(random.uniform(5, 10))
                except Exception as e:
                    print(f"Error processing product: {e}")

            return products

        except Exception as e:
            print(f"Error searching for: {e}")
            return []

    def _search_products_selenium(
        self, category, subcategory, item, search_url, count=2
    ):
        """Search using Selenium WebDriver with improved handling of stale elements"""
        products = []

        try:
            # Navigate to search page
            self.driver.get(search_url)

            # More extensive wait and human simulation before interacting
            time.sleep(random.uniform(8, 15))  # Longer initial wait

            # Scroll gradually
            for _ in range(5):
                self.driver.execute_script(
                    f"window.scrollBy(0, {random.randint(100, 300)});"
                )
                time.sleep(random.uniform(1, 3))

            # Take screenshot for debugging
            self.driver.save_screenshot(f"search_{category}_{item}.png")

            # Try multiple selectors to find products using JavaScript to avoid stale element issues
            product_urls = self.driver.execute_script(
                """
                var selectors = [
                    ".search-item-card-wrapper-gallery a[href*='/item/']", 
                    ".hm_bu a[href*='/item/']", 
                    ".jr_j4 a[href*='/item/']",
                    ".manhattan--container--1lP57Ag a[href*='/item/']", 
                    ".list--gallery--C2f2tvm a[href*='/item/']",
                    "a[href*='/item/']"
                ];
                
                var productUrls = [];
                
                for (var i = 0; i < selectors.length; i++) {
                    var elements = document.querySelectorAll(selectors[i]);
                    if (elements.length > 0) {
                        for (var j = 0; j < Math.min(elements.length, """
                + str(count)
                + """); j++) {
                            var href = elements[j].getAttribute('href');
                            if (href && href.includes('/item/')) {
                                // Fix relative URLs
                                if (href.startsWith('//')) {
                                    href = 'https:' + href;
                                } else if (href.startsWith('/')) {
                                    href = 'https://aliexpress.com' + href;
                                } else if (!href.startsWith('http')) {
                                    href = 'https://aliexpress.com/' + href;
                                }
                                
                                // Clean up double slashes (excluding protocol)
                                if (href.indexOf('://') > -1) {
                                    // Get everything after the protocol
                                    var parts = href.split('://');
                                    var protocol = parts[0] + '://';
                                    var rest = parts[1].replace(/\/\//g, '/');
                                    href = protocol + rest;
                                }
                                
                                productUrls.push(href);
                            }
                        }
                        
                        if (productUrls.length > 0) {
                            break;
                        }
                    }
                }
                
                return productUrls;
            """
            )

            if not product_urls:
                print("No products found. Taking screenshot for debugging...")
                self.driver.save_screenshot(f"debug_no_products_{category}_{item}.png")
                with open("page_source_no_products.html", "w", encoding="utf-8") as f:
                    f.write(self.driver.page_source)
                return []

            print(f"Found {len(product_urls)} products for {item} in {subcategory}")

            # Process each product URL
            for product_url in product_urls:
                try:
                    # Get product details
                    product_data = self.extract_product_details_selenium(product_url)

                    # Add category information
                    product_data["category"] = category
                    product_data["subcategory"] = subcategory
                    product_data["item_type"] = item

                    # Add to list and save
                    products.append(product_data)
                    self.save_product(product_data)

                    # Random delay between products
                    self.random_sleep(5, 10)

                except Exception as e:
                    print(f"Error processing product with Selenium: {e}")

            return products

        except Exception as e:
            print(f"Error in _search_products_selenium: {e}")
            return products

    def simulate_human_behavior(self):
        """Scroll randomly and move mouse to appear human-like"""
        try:
            # Random scroll
            for i in range(random.randint(3, 8)):
                scroll_amount = random.randint(300, 800)
                self.driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
                time.sleep(random.uniform(0.5, 2))

            # Random delay before proceeding
            time.sleep(random.uniform(2, 5))
        except Exception as e:
            print(f"Error simulating human behavior: {e}")

    def debug_page_selectors(self):
        """Print page source or take a screenshot to debug selectors"""
        try:
            # Save page source for debugging
            with open("debug_page.html", "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)

            # Take screenshot
            self.driver.save_screenshot("debug_screenshot.png")
            print("Debug files saved: debug_page.html and debug_screenshot.png")
        except Exception as e:
            print(f"Error debugging page: {e}")

    def extract_product_details(self, product_url):
        """Extract detailed information using requests"""
        if self.use_selenium:
            return self.extract_product_details_selenium(product_url)

        try:
            response = self.session.get(product_url, headers=self.headers, timeout=30)

            # Check for unusual traffic detection
            if (
                "unusual traffic" in response.text.lower()
                or "captcha" in response.text.lower()
            ):
                print(
                    "Unusual traffic detected on product page! Consider using Selenium mode."
                )
                return self._create_error_product(product_url)

            soup = BeautifulSoup(response.text, "html.parser")

            # Basic product information - updated selectors
            title = soup.select_one(
                "h1.product-title-text, .product-title, ._1Qg3M, .pdp-mod-product-title"
            )
            price = soup.select_one(
                ".product-price-value, ._12L_Hx, .pdp-mod-product-price"
            )
            description = soup.select_one(
                ".product-description, ._30PRb, .detail-desc, .pdp-mod-product-description"
            )

            # Image URLs - updated selectors
            main_images = []
            image_elements = soup.select(
                ".image-gallery img, .pdp-img img, ._3-0A8C img, .pdp-mod-product-image img"
            )
            for img in image_elements[:5]:
                src = img.get("src", img.get("data-src", ""))
                if src:
                    main_images.append(src)

            variant_images = []
            variant_elements = soup.select(
                ".sku-property-image img, .color-atc img, ._3Kg4LJ img, .sku-item img"
            )
            for img in variant_elements[:3]:
                src = img.get("src", img.get("data-src", ""))
                if src:
                    variant_images.append(src)

            # Additional details
            sku = soup.select_one("[data-sku-id], [data-product-id], [data-item-id]")
            sku_id = (
                sku.get(
                    "data-sku-id", sku.get("data-product-id", sku.get("data-item-id"))
                )
                if sku
                else f"ALI-{random.randint(100000, 999999)}"
            )

            product_data = {
                "title": title.text.strip() if title else "Unknown Product",
                "price": price.text.strip() if price else "Unknown Price",
                "description": description.text.strip()
                if description
                else "No description available",
                "product_url": product_url,
                "product_id": sku_id,
                "main_images": main_images,
                "variant_images": variant_images,
            }

            return product_data

        except Exception as e:
            print(f"Error extracting details from {product_url}: {e}")
            return self._create_error_product(product_url)

    def extract_product_details_selenium(self, product_url):
        """Extract detailed information using Selenium with improved error handling"""
        try:
            # Store current window handle
            original_window = self.driver.current_window_handle

            # Navigate to product page in a new tab
            self.driver.execute_script("window.open('');")
            self.driver.switch_to.window(self.driver.window_handles[1])
            self.driver.get(product_url)

            # Random delay to simulate human behavior
            self.random_sleep(8, 12)
            self.simulate_human_behavior()

            # Check for unusual traffic detection
            if (
                "unusual traffic" in self.driver.page_source.lower()
                or "captcha" in self.driver.page_source.lower()
            ):
                print("Unusual traffic detected on product page! Waiting...")
                time.sleep(60)  # Wait longer
                # Take screenshot for debugging
                self.driver.save_screenshot("captcha_detected.png")

                # Close tab and switch back to original
                self.driver.close()
                self.driver.switch_to.window(original_window)
                return self._create_error_product(product_url)

            # For debugging, save the page source
            with open("product_page_source.html", "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)

            # Take a screenshot for debugging
            self.driver.save_screenshot("product_page.png")

            # Extract title - Updated for 2025 AliExpress structure
            try:
                title = self.driver.execute_script("""
                    // Try multiple selectors for title, including the new 2025 structure
                    var titleSelectors = [
                        'h1[data-pl="product-title"]',
                        'h1.product-title-text', 
                        '.product-title', 
                        '._1Qg3M', 
                        '.pdp-mod-product-title',
                        'h1',
                        '.detail-title'
                    ];
                    
                    for (var i = 0; i < titleSelectors.length; i++) {
                        var element = document.querySelector(titleSelectors[i]);
                        if (element && element.textContent.trim()) {
                            return element.textContent.trim();
                        }
                    }
                    
                    return "Unknown Product";
                """)
            except Exception as e:
                print(f"Error extracting title with JS: {e}")
                title = "Unknown Product"

            # Get price - Updated for 2025 AliExpress structure
            try:
                price = self.driver.execute_script("""
                    // Try multiple selectors for price
                    var priceSelectors = [
                        '.pdp-info-right .price',
                        '.product-price-value', 
                        '._12L_Hx', 
                        '.pdp-mod-product-price',
                        '.uniform-banner-box-price',
                        '.product-price-current',
                        '.product-price',
                        '.manhattan--price--WvaUgDY'
                    ];
                    
                    for (var i = 0; i < priceSelectors.length; i++) {
                        var element = document.querySelector(priceSelectors[i]);
                        if (element && element.textContent.trim()) {
                            return element.textContent.trim();
                        }
                    }
                    
                    return "Unknown Price";
                """)
            except Exception as e:
                print(f"Error extracting price with JS: {e}")
                price = "Unknown Price"

            # Get description - Updated for 2025 AliExpress structure
            try:
                description = self.driver.execute_script("""
                    // Try multiple selectors for description
                    var descSelectors = [
                        '.product-description', 
                        '._30PRb', 
                        '.detail-desc',
                        '.pdp-mod-product-description',
                        '.product-desc',
                        '#product-description',
                        '.pdp-overview-content'
                    ];
                    
                    for (var i = 0; i < descSelectors.length; i++) {
                        var element = document.querySelector(descSelectors[i]);
                        if (element && element.textContent.trim()) {
                            return element.textContent.trim();
                        }
                    }
                    
                    return "No description available";
                """)
            except Exception as e:
                print(f"Error extracting description with JS: {e}")
                description = "No description available"

            # Extract image URLs - Updated for 2025 AliExpress structure
            try:
                main_images = self.driver.execute_script("""
                    // Direct extract from the slider images in the 2025 structure
                    var images = [];
                    
                    // First try new 2025 structure
                    var newSliderItems = document.querySelectorAll('.slider--item--RpyeewA img, .magnifier--image--RM17RL2');
                    if (newSliderItems && newSliderItems.length > 0) {
                        for (var i = 0; i < newSliderItems.length; i++) {
                            var src = newSliderItems[i].getAttribute('src');
                            if (src && src.trim() !== '') {
                                // Clean up the src to get base image URL (remove size restrictions)
                                src = src.split('_')[0];
                                // Remove .avif or other format extensions
                                if (src.endsWith('.avif')) {
                                    src = src.slice(0, -5);
                                }
                                // Ensure it has an image extension
                                if (!src.endsWith('.jpg') && !src.endsWith('.jpeg') && !src.endsWith('.png') && !src.endsWith('.webp')) {
                                    src = src + '.jpg';
                                }
                                
                                if (images.indexOf(src) === -1) {
                                    images.push(src);
                                }
                            }
                        }
                    }
                    
                    // If no images found, try older selectors
                    if (images.length === 0) {
                        var imageSelectors = [
                            '.image-gallery img', 
                            '.pdp-img img', 
                            '._3-0A8C img',
                            '.pdp-mod-product-image img',
                            '.img-view-item img',
                            '.images-view-item img'
                        ];
                        
                        for (var j = 0; j < imageSelectors.length; j++) {
                            var imgElements = document.querySelectorAll(imageSelectors[j]);
                            if (imgElements.length > 0) {
                                for (var i = 0; i < Math.min(imgElements.length, 10); i++) {
                                    var src = imgElements[i].getAttribute('src') || imgElements[i].getAttribute('data-src');
                                    // Try lazily loaded images
                                    if (!src) {
                                        src = imgElements[i].dataset.src || imgElements[i].dataset.lazyload;
                                    }
                                    
                                    if (src && images.indexOf(src) === -1) {
                                        // Fix relative URLs
                                        if (src.startsWith('//')) {
                                            src = 'https:' + src;
                                        }
                                        
                                        // Process URL to get base image
                                        src = src.split('_')[0];
                                        if (src.endsWith('.avif')) {
                                            src = src.slice(0, -5);
                                        }
                                        if (!src.endsWith('.jpg') && !src.endsWith('.jpeg') && !src.endsWith('.png') && !src.endsWith('.webp')) {
                                            src = src + '.jpg';
                                        }
                                        
                                        // Add only if not already in the list
                                        if (src.startsWith('http') && images.indexOf(src) === -1) {
                                            images.push(src);
                                        }
                                    }
                                }
                                if (images.length > 0) break;
                            }
                        }
                    }
                    
                    // Also try looking for images in background-image style properties if still no images
                    if (images.length === 0) {
                        var backgroundImgElements = document.querySelectorAll('.img-view-item, .image-view-item');
                        for (var i = 0; i < Math.min(backgroundImgElements.length, 5); i++) {
                            var style = window.getComputedStyle(backgroundImgElements[i]);
                            var url = style.backgroundImage;
                            if (url && url !== 'none') {
                                url = url.replace(/^url\\(['"]?/, '').replace(/['"]?\\)$/, '');
                                if (url.startsWith('//')) {
                                    url = 'https:' + url;
                                }
                                
                                // Process URL
                                url = url.split('_')[0];
                                if (url.endsWith('.avif')) {
                                    url = url.slice(0, -5);
                                }
                                if (!url.endsWith('.jpg') && !url.endsWith('.jpeg') && !url.endsWith('.png') && !url.endsWith('.webp')) {
                                    url = url + '.jpg';
                                }
                                
                                if (url.startsWith('http') && images.indexOf(url) === -1) {
                                    images.push(url);
                                }
                            }
                        }
                    }
                    
                    return images;
                """)
            except Exception as e:
                print(f"Error extracting main images with JS: {e}")
                main_images = []

            # Extract variant images - Updated for 2025 AliExpress structure based on the HTML snippet
            try:
                variant_images = self.driver.execute_script("""
                    // Updated for 2025 structure - look for color/variant thumbnails
                    var varImages = [];
                    
                    // First try the specific 2025 structure from the HTML snippet
                    var skuItemImages = document.querySelectorAll('.sku-item--box--Lrl6ZXB .sku-item--image--jMUnnGA img');
                    if (skuItemImages && skuItemImages.length > 0) {
                        for (var i = 0; i < skuItemImages.length; i++) {
                            var src = skuItemImages[i].getAttribute('src');
                            if (src && src.trim() !== '') {
                                // Process URL to get base image
                                src = src.split('_')[0];
                                if (src.endsWith('.avif')) {
                                    src = src.slice(0, -5);
                                }
                                if (!src.endsWith('.jpg') && !src.endsWith('.jpeg') && !src.endsWith('.png') && !src.endsWith('.webp')) {
                                    src = src + '.jpg';
                                }
                                
                                if (varImages.indexOf(src) === -1) {
                                    varImages.push(src);
                                }
                            }
                        }
                    }
                    
                    // Also try the property-item selectors
                    if (varImages.length === 0) {
                        var propertyItems = document.querySelectorAll('.property-item--content--N2pGZlv img, .property-item--imgwrap--RVrqA7K img');
                        if (propertyItems && propertyItems.length > 0) {
                            for (var i = 0; i < propertyItems.length; i++) {
                                var src = propertyItems[i].getAttribute('src');
                                if (src && src.trim() !== '') {
                                    // Process URL
                                    src = src.split('_')[0];
                                    if (src.endsWith('.avif')) {
                                        src = src.slice(0, -5);
                                    }
                                    if (!src.endsWith('.jpg') && !src.endsWith('.jpeg') && !src.endsWith('.png') && !src.endsWith('.webp')) {
                                        src = src + '.jpg';
                                    }
                                    
                                    if (varImages.indexOf(src) === -1) {
                                        varImages.push(src);
                                    }
                                }
                            }
                        }
                    }
                    
                    // If no variant images found, try older selectors
                    if (varImages.length === 0) {
                        var variantSelectors = [
                            '.sku-property-image img', 
                            '.color-atc img', 
                            '._3Kg4LJ img',
                            '.sku-item img',
                            '.sku-property-item img'
                        ];
                        
                        for (var j = 0; j < variantSelectors.length; j++) {
                            var imgElements = document.querySelectorAll(variantSelectors[j]);
                            if (imgElements.length > 0) {
                                for (var i = 0; i < Math.min(imgElements.length, 10); i++) {
                                    var src = imgElements[i].getAttribute('src') || imgElements[i].getAttribute('data-src');
                                    // Try lazily loaded images
                                    if (!src) {
                                        src = imgElements[i].dataset.src || imgElements[i].dataset.lazyload;
                                    }
                                    
                                    if (src && varImages.indexOf(src) === -1) {
                                        // Fix relative URLs
                                        if (src.startsWith('//')) {
                                            src = 'https:' + src;
                                        }
                                        
                                        // Process URL
                                        src = src.split('_')[0];
                                        if (src.endsWith('.avif')) {
                                            src = src.slice(0, -5);
                                        }
                                        if (!src.endsWith('.jpg') && !src.endsWith('.jpeg') && !src.endsWith('.png') && !src.endsWith('.webp')) {
                                            src = src + '.jpg';
                                        }
                                        
                                        // Add only if not already in the list and is a valid URL
                                        if (src.startsWith('http') && varImages.indexOf(src) === -1) {
                                            varImages.push(src);
                                        }
                                    }
                                }
                                if (varImages.length > 0) break;
                            }
                        }
                    }
                    
                    return varImages;
                """)
            except Exception as e:
                print(f"Error extracting variant images with JS: {e}")
                variant_images = []

            # Generate or extract product ID
            try:
                sku_id = self.driver.execute_script("""
                    // Try to extract from various data attributes
                    var idAttributes = ['data-sku-id', 'data-product-id', 'data-item-id'];
                    
                    for (var i = 0; i < idAttributes.length; i++) {
                        var element = document.querySelector('[' + idAttributes[i] + ']');
                        if (element) {
                            var id = element.getAttribute(idAttributes[i]);
                            if (id) return id;
                        }
                    }
                    
                    // Try to extract from URL
                    var url = window.location.href;
                    if (url.includes('item/')) {
                        var parts = url.split('item/');
                        if (parts.length > 1) {
                            var idPart = parts[1].split('.')[0];
                            if (/^\\d+$/.test(idPart)) {
                                return idPart;
                            }
                        }
                    }
                    
                    // Generate random ID if all else fails
                    return 'ALI-' + Math.floor(Math.random() * 900000 + 100000);
                """)
            except Exception as e:
                print(f"Error extracting SKU ID with JS: {e}")
                sku_id = f"ALI-{random.randint(100000, 999999)}"

            # Process the extracted images to ensure proper format
            main_images = [self._fix_image_url(url) for url in main_images if url]
            variant_images = [self._fix_image_url(url) for url in variant_images if url]

            # Close product tab and switch back to original window
            self.driver.close()
            self.driver.switch_to.window(original_window)

            product_data = {
                "title": title,
                "price": price,
                "description": description,
                "product_url": product_url,
                "product_id": sku_id,
                "main_images": main_images,
                "variant_images": variant_images,
            }

            print(f"Extracted product: {title}")
            print(
                f"Images found: {len(main_images)} main, {len(variant_images)} variants"
            )

            return product_data

        except Exception as e:
            print(f"Error extracting details with Selenium from {product_url}: {e}")
            # Try to close tab and switch back if possible
            try:
                if len(self.driver.window_handles) > 1:
                    self.driver.close()
                    self.driver.switch_to.window(self.driver.window_handles[0])
            except:
                pass
            return self._create_error_product(product_url)

    def _fix_image_url(self, url):
        """Clean and standardize image URLs"""
        if not url:
            return ""

        # Fix protocol-relative URLs
        if url.startswith("//"):
            url = "https:" + url

        # Extract base URL (remove size restrictions)
        parts = url.split("_")
        base_url = parts[0]

        # Remove .avif extension if present
        if base_url.endswith(".avif"):
            base_url = base_url[:-5]

        # Ensure it has an image extension
        if not any(
            base_url.endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp"]
        ):
            base_url += ".jpg"

        return base_url

    def _create_error_product(self, product_url):
        """Create a placeholder product when extraction fails"""
        return {
            "title": "Error fetching product",
            "price": "Unknown",
            "description": "Failed to retrieve product details",
            "product_url": product_url,
            "product_id": f"ERROR-{random.randint(10000, 99999)}",
            "main_images": [],
            "variant_images": [],
        }

    def save_product(self, product_data):
        """Save product data to a structured format on disk"""
        # Create product folder with sanitized name
        product_name = product_data["title"][:50].replace("/", "-").replace("\\", "-")
        product_name = "".join(
            c if c.isalnum() or c in "- " else "_" for c in product_name
        )
        product_folder = os.path.join(
            self.output_dir, f"{product_data['product_id']}_{product_name}"
        )

        if not os.path.exists(product_folder):
            os.makedirs(product_folder)

        # Create folders for images
        product_main_images = os.path.join(product_folder, "main_images")
        product_variant_images = os.path.join(product_folder, "variant_images")

        if not os.path.exists(product_main_images):
            os.makedirs(product_main_images)
        if not os.path.exists(product_variant_images):
            os.makedirs(product_variant_images)

        # Save product info as text file
        info_file_path = os.path.join(product_folder, "info_product.txt")
        with open(info_file_path, "w", encoding="utf-8") as file:
            file.write(f"### Product name\n{product_data['title']}\n\n")
            file.write(f"### Product ID\n{product_data['product_id']}\n\n")
            file.write(f"### Link\n{product_data['product_url']}\n\n")
            file.write(f"### Price\n{product_data['price']}\n\n")
            file.write(f"### Description\n{product_data['description']}\n\n")
            file.write(f"### Category\n{product_data.get('category', 'N/A')}\n\n")
            file.write(f"### Subcategory\n{product_data.get('subcategory', 'N/A')}\n\n")
            file.write(f"### Item Type\n{product_data.get('item_type', 'N/A')}\n\n")

        # Also save as JSON for easier processing
        json_file_path = os.path.join(product_folder, "product_data.json")
        with open(json_file_path, "w", encoding="utf-8") as file:
            json.dump(product_data, file, indent=4, ensure_ascii=False)

        # Download images
        self.download_images(product_data["main_images"], product_main_images, "main")
        self.download_images(
            product_data["variant_images"], product_variant_images, "variant"
        )

        print(f"Saved product: {product_data['title']}")
        return product_folder


def scrape_all_categories(use_selenium=True, proxy=None):
    scraper = AliExpressScraper(output_dir="categories", use_selenium=use_selenium)

    try:
        category_structure = [
            {
                "name": "Apparel & Fashion",
                "subcategories": [
                    {
                        "name": "Men's Clothing",
                        "items": [
                            "T-Shirts",
                            "Shirts",
                            "Jeans",
                            "Suits",
                            "Jackets",
                            "Underwear",
                        ],
                    },
                    {
                        "name": "Women's Clothing",
                        "items": [
                            "Dresses",
                            "Tops",
                            "Jeans",
                            "Skirts",
                            "Abayas",
                            "Suits",
                        ],
                    },
                    {
                        "name": "Children's Clothing",
                        "items": ["Babywear", "Boys' Clothing", "Girls' Clothing"],
                    },
                    {
                        "name": "Fashion Accessories",
                        "items": [
                            "Belts",
                            "Scarves",
                            "Hats",
                            "Sunglasses",
                            "Gloves",
                            "Ties",
                        ],
                    },
                    {
                        "name": "Footwear",
                        "items": [
                            "Men's",
                            "Women's",
                            "Kids'",
                            "Sports",
                            "Formal",
                            "Casual",
                        ],
                    },
                ],
            },
            {
                "name": "Electronics & Appliances",
                "subcategories": [
                    {
                        "name": "Consumer Electronics",
                        "items": ["Smartphones", "TVs", "Cameras", "Audio Equipment"],
                    },
                    {
                        "name": "Home Appliances",
                        "items": [
                            "Refrigerators",
                            "Washing Machines",
                            "Ovens",
                            "Microwaves",
                        ],
                    },
                    {
                        "name": "Computer & Office Equipment",
                        "items": [
                            "Laptops",
                            "Monitors",
                            "Printers",
                            "Networking Devices",
                        ],
                    },
                    {
                        "name": "Electrical Components",
                        "items": ["Cables", "Switches", "Batteries", "Lighting"],
                    },
                ],
            },
            {
                "name": "Home & Garden",
                "subcategories": [
                    {
                        "name": "Furniture",
                        "items": ["Living Room", "Bedroom", "Outdoor", "Office"],
                    },
                    {
                        "name": "Home Decor",
                        "items": ["Wall Art", "Clocks", "Curtains", "Rugs", "Mirrors"],
                    },
                    {
                        "name": "Kitchenware",
                        "items": [
                            "Cookware",
                            "Utensils",
                            "Storage",
                            "Small Appliances",
                        ],
                    },
                    {
                        "name": "Gardening Supplies",
                        "items": ["Pots", "Plants", "Seeds", "Tools", "Irrigation"],
                    },
                    {
                        "name": "Cleaning & Utility",
                        "items": ["Tools", "Supplies", "Vacuums", "Organizers"],
                    },
                ],
            },
            {
                "name": "Beauty & Personal Care",
                "subcategories": [
                    {
                        "name": "Skincare",
                        "items": ["Creams", "Serums", "Face Wash", "Masks"],
                    },
                    {
                        "name": "Haircare",
                        "items": ["Shampoos", "Conditioners", "Styling Products"],
                    },
                    {
                        "name": "Makeup",
                        "items": ["Lipstick", "Foundation", "Eyeshadow", "Brushes"],
                    },
                    {
                        "name": "Fragrances",
                        "items": ["Perfumes", "Colognes", "Deodorants"],
                    },
                    {
                        "name": "Personal Hygiene",
                        "items": ["Soaps", "Sanitary Products", "Toothpaste", "Razors"],
                    },
                ],
            },
            {
                "name": "Health & Wellness",
                "subcategories": [
                    {
                        "name": "Vitamins & Supplements",
                        "items": ["Vitamins & Supplements"],
                    },
                    {
                        "name": "Medical Supplies",
                        "items": ["PPE", "Thermometers", "First Aid Kits"],
                    },
                    {
                        "name": "Fitness Equipment",
                        "items": ["Weights", "Yoga Mats", "Resistance Bands"],
                    },
                    {
                        "name": "Herbal & Natural Remedies",
                        "items": ["Herbal & Natural Remedies"],
                    },
                    {
                        "name": "Massage & Relaxation Tools",
                        "items": ["Massage & Relaxation Tools"],
                    },
                ],
            },
            {
                "name": "Food & Beverages",
                "subcategories": [
                    {
                        "name": "Packaged Foods",
                        "items": [
                            "Snacks",
                            "Canned Goods",
                            "Cereals",
                            "Instant Noodles",
                        ],
                    },
                    {
                        "name": "Beverages",
                        "items": [
                            "Tea",
                            "Coffee",
                            "Juices",
                            "Soft Drinks",
                            "Energy Drinks",
                        ],
                    },
                    {
                        "name": "Fresh Produce",
                        "items": ["Fruits", "Vegetables", "Meat", "Seafood"],
                    },
                    {
                        "name": "Gourmet & Organic Foods",
                        "items": ["Gourmet & Organic Foods"],
                    },
                    {"name": "Spices & Condiments", "items": ["Spices & Condiments"]},
                ],
            },
            {
                "name": "Baby & Kids",
                "subcategories": [
                    {
                        "name": "Baby Clothing & Accessories",
                        "items": ["Baby Clothing & Accessories"],
                    },
                    {"name": "Diapers & Wipes", "items": ["Diapers & Wipes"]},
                    {
                        "name": "Feeding Supplies",
                        "items": ["Bottles", "Sippy Cups", "Food Warmers"],
                    },
                    {"name": "Toys & Games", "items": ["Toys & Games"]},
                    {
                        "name": "Strollers, Car Seats, Furniture",
                        "items": ["Strollers, Car Seats, Furniture"],
                    },
                ],
            },
            {
                "name": "Toys, Hobbies & DIY",
                "subcategories": [
                    {"name": "Educational Toys", "items": ["Educational Toys"]},
                    {"name": "Outdoor Toys", "items": ["Outdoor Toys"]},
                    {
                        "name": "Board Games & Puzzles",
                        "items": ["Board Games & Puzzles"],
                    },
                    {
                        "name": "DIY Tools",
                        "items": ["Power Tools", "Hand Tools", "Kits"],
                    },
                    {
                        "name": "Craft Supplies",
                        "items": ["Paint", "Beads", "Fabrics", "Brushes"],
                    },
                ],
            },
            {
                "name": "Sports & Outdoor",
                "subcategories": [
                    {"name": "Sportswear", "items": ["Sportswear"]},
                    {"name": "Footwear", "items": ["Footwear"]},
                    {"name": "Fitness Gear", "items": ["Fitness Gear"]},
                    {"name": "Camping & Hiking", "items": ["Camping & Hiking"]},
                    {
                        "name": "Bicycles & Accessories",
                        "items": ["Bicycles & Accessories"],
                    },
                    {
                        "name": "Team Sports Equipment",
                        "items": ["Team Sports Equipment"],
                    },
                ],
            },
            {
                "name": "Automotive & Motorcycle",
                "subcategories": [
                    {
                        "name": "Auto Parts",
                        "items": ["Tires", "Brakes", "Engine Components"],
                    },
                    {
                        "name": "Motorbike Accessories",
                        "items": ["Motorbike Accessories"],
                    },
                    {
                        "name": "Car Electronics",
                        "items": ["Stereos", "Dashcams", "GPS"],
                    },
                    {"name": "Oils & Fluids", "items": ["Oils & Fluids"]},
                    {
                        "name": "Car Care & Maintenance",
                        "items": ["Car Care & Maintenance"],
                    },
                ],
            },
            {
                "name": "Industrial & Machinery",
                "subcategories": [
                    {
                        "name": "Construction Equipment",
                        "items": ["Construction Equipment"],
                    },
                    {"name": "Manufacturing Tools", "items": ["Manufacturing Tools"]},
                    {"name": "Farming Equipment", "items": ["Farming Equipment"]},
                    {"name": "Safety Gear", "items": ["Safety Gear"]},
                    {
                        "name": "Pipes, Valves & Fittings",
                        "items": ["Pipes, Valves & Fittings"],
                    },
                ],
            },
            {
                "name": "Office & School Supplies",
                "subcategories": [
                    {"name": "Stationery", "items": ["Stationery"]},
                    {"name": "Office Furniture", "items": ["Office Furniture"]},
                    {"name": "Printers & Supplies", "items": ["Printers & Supplies"]},
                    {
                        "name": "School Backpacks & Kits",
                        "items": ["School Backpacks & Kits"],
                    },
                    {
                        "name": "Notebooks, Files & Folders",
                        "items": ["Notebooks, Files & Folders"],
                    },
                ],
            },
            {
                "name": "Jewelry & Watches",
                "subcategories": [
                    {
                        "name": "Gold, Silver, Platinum",
                        "items": ["Gold, Silver, Platinum"],
                    },
                    {"name": "Fashion Jewelry", "items": ["Fashion Jewelry"]},
                    {"name": "Watches", "items": ["Smartwatches", "Luxury", "Casual"]},
                    {"name": "Body Jewelry", "items": ["Body Jewelry"]},
                    {
                        "name": "Custom & Handmade Pieces",
                        "items": ["Custom & Handmade Pieces"],
                    },
                ],
            },
            {
                "name": "Luggage & Travel",
                "subcategories": [
                    {"name": "Suitcases & Bags", "items": ["Suitcases & Bags"]},
                    {"name": "Backpacks", "items": ["Backpacks"]},
                    {
                        "name": "Travel Accessories",
                        "items": ["Adapters", "Organizers", "Locks"],
                    },
                ],
            },
            {
                "name": "Pet Supplies",
                "subcategories": [
                    {"name": "Dog Supplies", "items": ["Dog Supplies"]},
                    {"name": "Cat Supplies", "items": ["Cat Supplies"]},
                    {"name": "Pet Food", "items": ["Pet Food"]},
                    {"name": "Pet Toys & Grooming", "items": ["Pet Toys & Grooming"]},
                    {
                        "name": "Aquarium & Bird Supplies",
                        "items": ["Aquarium & Bird Supplies"],
                    },
                ],
            },
            {
                "name": "Gifts & Occasions",
                "subcategories": [
                    {
                        "name": "Seasonal Gifts",
                        "items": [
                            "Christmas",
                            "Eid",
                            "Diwali",
                            "Chinese New Year",
                        ],
                    },
                    {"name": "Party Supplies", "items": ["Party Supplies"]},
                    {"name": "Gift Wrapping", "items": ["Gift Wrapping"]},
                    {"name": "Customizable Gifts", "items": ["Customizable Gifts"]},
                    {
                        "name": "Wedding & Event Decor",
                        "items": ["Wedding & Event Decor"],
                    },
                ],
            },
        ]

        # Track progress
        total_products = 0
        target_products = 1000
        products_per_category = 5

        # Iterate through the category structure
        for category in category_structure:
            category_name = category["name"]

            for subcategory in category["subcategories"]:
                subcategory_name = subcategory["name"]

                for item in subcategory["items"]:
                    # Try multiple times with increasing delays
                    for attempt in range(3):  # Try 3 times
                        try:
                            print(
                                f"Attempt {attempt + 1} for {item} in {subcategory_name}"
                            )
                            products = scraper.search_products(
                                category_name,
                                subcategory_name,
                                item,
                                count=products_per_category,
                                proxy=proxy,
                            )

                            if products:
                                total_products += len(products)
                                print(
                                    f"Successfully scraped {len(products)} products for {item}"
                                )
                                break  # Exit retry loop if successful
                            else:
                                # Increase wait time between retries
                                wait_time = (attempt + 1) * 20
                                print(
                                    f"No products found. Waiting {wait_time} seconds before retry..."
                                )
                                time.sleep(wait_time)
                        except Exception as e:
                            print(f"Error during scrape attempt {attempt + 1}: {e}")
                            time.sleep((attempt + 1) * 30)  # Longer wait after error
                            # Check if we've reached our target
                    if total_products >= target_products:
                        print(
                            f"Reached target of {target_products} products. Stopping."
                        )
                        break

                # Check again if we've reached our target
                if total_products >= target_products:
                    break

            # Final check if we've reached our target
            if total_products >= target_products:
                break

        print(f"Scraping complete! Total products scraped: {total_products}")
    except Exception as e:
        print(f"Error in scrape_all_categories: {e}")
    finally:
        # Always close the scraper properly
        scraper.close()

    return total_products


def main():
    """Main function to run the scraper"""
    import argparse

    parser = argparse.ArgumentParser(description="AliExpress Product Scraper")
    parser.add_argument(
        "--output",
        default="aliexpress_products",
        help="Output directory for scraped products",
    )
    parser.add_argument(
        "--selenium",
        action="store_true",
        help="Use Selenium for scraping (recommended)",
    )
    parser.add_argument(
        "--proxy", help="Proxy to use (format: http://user:pass@host:port)"
    )
    parser.add_argument(
        "--count", type=int, default=20, help="Target number of products to scrape"
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")

    args = parser.parse_args()

    print("AliExpress Product Scraper")
    print("=========================")
    print(f"Output directory: {args.output}")
    print(f"Using Selenium: {args.selenium}")
    print(f"Using proxy: {'Yes' if args.proxy else 'No'}")
    print(f"Target product count: {args.count}")
    print("=========================")

    try:
        if args.debug:
            # Test a single product extraction
            scraper = AliExpressScraper(
                output_dir=args.output, use_selenium=args.selenium
            )
            product = scraper.extract_product_details_selenium(
                "https://www.aliexpress.com/item/1005002591508351.html"
            )
            scraper.save_product(product)
            scraper.close()
        else:
            # Full category scraping
            total = scrape_all_categories(use_selenium=args.selenium, proxy=args.proxy)
            print(f"Successfully scraped {total} products")
    except KeyboardInterrupt:
        print("\nScraping interrupted by user")
    except Exception as e:
        print(f"Error in main function: {e}")


class CategoryScraper(AliExpressScraper):
    """Extension of the base scraper with additional category navigation capabilities"""

    def __init__(self, output_dir="category_products", use_selenium=True):
        super().__init__(output_dir=output_dir, use_selenium=use_selenium)
        self.category_base_url = "https://www.aliexpress.com/category/"

    def scrape_category_page(self, category_id, page=1, items_per_page=60):
        """Scrape products from a specific category page"""
        url = f"{self.category_base_url}{category_id}.html?page={page}&trafficChannel=main"

        print(f"Scraping category ID {category_id}, page {page}")

        if not self.use_selenium:
            print("Category page scraping requires Selenium. Enabling Selenium.")
            self.use_selenium = True
            self.setup_selenium()

        try:
            # Navigate to the category page
            self.driver.get(url)

            # Wait for page to load and simulate human behavior
            self.random_sleep(10, 15)
            self.simulate_human_behavior()

            # Find all product cards
            product_selectors = [
                ".items-list .item",
                ".product-card",
                ".manhattan--container--1lP57Ag",
                ".JIIxO",
            ]

            product_links = []

            # Try each selector
            for selector in product_selectors:
                try:
                    product_elements = self.driver.find_elements(
                        By.CSS_SELECTOR, selector
                    )
                    if product_elements:
                        for product in product_elements[:items_per_page]:
                            try:
                                # Try to get link directly
                                link = product.get_attribute("href")

                                # If not, find <a> element
                                if not link:
                                    link_element = product.find_element(
                                        By.CSS_SELECTOR, "a"
                                    )
                                    link = link_element.get_attribute("href")

                                if link and "item" in link:
                                    product_links.append(link)
                            except:
                                continue
                        break
                except Exception as e:
                    print(f"Selector {selector} failed: {e}")
                    continue

            print(f"Found {len(product_links)} product links")

            # Process each product link
            products = []
            for link in product_links:
                try:
                    product_data = self.extract_product_details_selenium(link)

                    # Add category info
                    product_data["category_id"] = category_id

                    # Save product
                    self.save_product(product_data)
                    products.append(product_data)

                    # Random delay
                    self.random_sleep(5, 10)
                except Exception as e:
                    print(f"Error processing product {link}: {e}")

            return products

        except Exception as e:
            print(f"Error scraping category page: {e}")
            return []


def bulk_category_scrape(category_ids, pages_per_category=2, use_selenium=True):
    """Scrape multiple categories with pagination"""
    scraper = CategoryScraper(output_dir="bulk_categories", use_selenium=use_selenium)

    total_products = 0

    try:
        for category_id in category_ids:
            for page in range(1, pages_per_category + 1):
                try:
                    print(
                        f"Scraping category {category_id}, page {page}/{pages_per_category}"
                    )
                    products = scraper.scrape_category_page(category_id, page=page)
                    total_products += len(products)

                    # Add longer delay between pages
                    time.sleep(random.uniform(30, 60))
                except Exception as e:
                    print(f"Error on category {category_id}, page {page}: {e}")
                    continue
    except Exception as e:
        print(f"Error in bulk scraping: {e}")
    finally:
        scraper.close()

    print(f"Bulk scraping complete! Total products: {total_products}")
    return total_products


if __name__ == "__main__":
    main()
