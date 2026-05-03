app_urls = {
    "Google":"https://www.google.com",
    "Facebook":"https://www.facebook.com",
    "YouTube":"https://www.youtube.com",
    "TikTok":"https://www.tiktok.com",
    "Instagram":"https://www.instagram.com",
    "X":"https://www.x.com"
}

def scrapeUrl(driver, *args, **kwargs):
    url = kwargs.get("url","https://devgadbadr.me")
    driver.get(url)