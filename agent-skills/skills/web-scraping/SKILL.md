---
name: web-scraping
description: The process of extracting data from websites in an efficient, ethical, and legal manner while respecting site owners' rules and avoiding blocks.
---

# Web Scraping

## Overview

Web scraping involves programmatically retrieving data from websites. In 2025 and beyond, best practices focus on balancing data extraction with respect for website policies, legal considerations, and technical efficiency. This skill covers the principles and techniques necessary to build reliable, ethical scrapers that avoid IP bans, CAPTCHAs, and legal pitfalls while delivering high-quality structured data.

## When to Use

- When you need to collect publicly available data from websites that do not provide a dedicated API.
- For market research, price monitoring, sentiment analysis, or aggregating content from multiple sources.
- To support data science projects, business intelligence, or academic research requiring large-scale web data.
- Avoid using web scraping for copyrighted content without permission, protected login areas, or when it would violate a website’s terms of service or applicable laws (e.g., GDPR).

## Process

1. **Understand Legal & Ethical Boundaries**  
   - Review the website’s `robots.txt` and Terms of Service.  
   - Ensure data collection is legal in your jurisdiction (e.g., avoid scraping personally identifiable information without consent).  
   - Respect copyright and data ownership: do not republish scraped data without permission.

2. **Choose the Right Tools & Libraries**  
   - For static pages: Python with Beautiful Soup, Scrapy, or Node.js with Cheerio.  
   - For dynamic content: use headless browsers like Selenium, Puppeteer, Playwright, or Pyppeteer.  
   - For large-scale scraping: consider Scrapy, or use APIs and proxies (residential/mobile) to avoid blocking.

3. **Implement Polite Scraping Practices**  
   - Set a reasonable request rate (e.g., add delays between requests).  
   - Rotate User-Agent strings and IP addresses via proxies.  
   - Handle errors gracefully (retry with exponential backoff, monitor HTTP status codes).  
   - Avoid scraping during peak hours if possible.

4. **Extract & Structure Data**  
   - Parse HTML using CSS selectors or XPath.  
   - Clean, transform, and store data in a structured format (CSV, JSON, database).  
   - Handle pagination, infinite scroll, and dynamic content loading.

5. **Monitor & Maintain**  
   - Set up alerts for changes in website structure (e.g., new selectors) or blocking.  
   - Regularly update your script to adapt to website modifications.  
   - Log scraping activity for auditing and debugging.

## Verification

- **Data Quality Check**: Compare a sample of scraped data against the source to ensure accuracy, completeness, and consistency.  
- **Legal Compliance Review**: Verify that your scraping does not violate `robots.txt`, Terms of Service, or data protection laws.  
- **Performance & Reliability**: Confirm that your scraper runs without frequent blocks, uses acceptable resources, and meets your required throughput.  
- **Ethical Validation**: Ensure you are not overloading the target server; check server logs or use tools to monitor your impact.