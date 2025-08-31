"""
Web Research Agent - Controlled Internet Access for Sanaa Projects
Provides safe, controlled access to external resources and documentation
"""
from __future__ import annotations
import asyncio
import json
import re
import time
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import hashlib
import urllib.parse

from coding_swarm_agents.base import Agent


class SafeWebClient:
    """Controlled web client with security restrictions"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.allowed_domains = config.get('allowed_domains', [
            'docs.npmjs.com',
            'reactjs.org',
            'laravel.com',
            'flutter.dev',
            'developer.mozilla.org',
            'stackoverflow.com',
            'github.com',
            'pypi.org',
            'pub.dev'
        ])

        self.request_timeout = config.get('request_timeout', 10)
        self.max_content_length = config.get('max_content_length', 50000)
        self.cache_ttl = config.get('cache_ttl', 3600)  # 1 hour

        # Content type restrictions
        self.allowed_content_types = [
            'text/html',
            'application/json',
            'text/plain',
            'application/xml'
        ]

        # Rate limiting
        self.requests_per_minute = config.get('requests_per_minute', 10)
        self.request_history = []

    def _is_domain_allowed(self, url: str) -> bool:
        """Check if domain is in allowed list"""
        try:
            parsed = urllib.parse.urlparse(url)
            domain = parsed.netloc.lower()

            # Check exact matches
            if domain in self.allowed_domains:
                return True

            # Check subdomain matches
            for allowed in self.allowed_domains:
                if domain.endswith('.' + allowed):
                    return True

            return False
        except:
            return False

    def _rate_limit_check(self) -> bool:
        """Check if request is within rate limits"""
        now = time.time()
        # Remove old requests
        self.request_history = [t for t in self.request_history if now - t < 60]

        return len(self.request_history) < self.requests_per_minute

    async def safe_get(self, url: str) -> Optional[Dict[str, Any]]:
        """Safely fetch content from allowed domains"""
        if not self._is_domain_allowed(url):
            return {
                'error': 'Domain not allowed',
                'allowed_domains': self.allowed_domains
            }

        if not self._rate_limit_check():
            return {
                'error': 'Rate limit exceeded',
                'retry_after': 60
            }

        try:
            import httpx

            # Add to request history
            self.request_history.append(time.time())

            async with httpx.AsyncClient(
                timeout=self.request_timeout,
                follow_redirects=True,
                headers={
                    'User-Agent': 'Sanaa-Research-Agent/1.0 (Educational)',
                    'Accept': 'text/html,application/json,text/plain,*/*'
                }
            ) as client:
                response = await client.get(url)

                if response.status_code != 200:
                    return {
                        'error': f'HTTP {response.status_code}',
                        'url': url
                    }

                content_type = response.headers.get('content-type', '').split(';')[0]
                if content_type not in self.allowed_content_types:
                    return {
                        'error': f'Content type not allowed: {content_type}',
                        'url': url
                    }

                content = response.text
                if len(content) > self.max_content_length:
                    content = content[:self.max_content_length] + "...[truncated]"

                return {
                    'url': url,
                    'content': content,
                    'content_type': content_type,
                    'status_code': response.status_code,
                    'headers': dict(response.headers)
                }

        except Exception as e:
            return {
                'error': str(e),
                'url': url
            }


class DocumentationCache:
    """Cache for documentation and web content"""

    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_key(self, url: str) -> str:
        """Generate cache key for URL"""
        return hashlib.md5(url.encode()).hexdigest()

    def get(self, url: str) -> Optional[Dict[str, Any]]:
        """Get cached content"""
        cache_key = self._get_cache_key(url)
        cache_file = self.cache_dir / f"{cache_key}.json"

        if not cache_file.exists():
            return None

        try:
            data = json.loads(cache_file.read_text())
            if time.time() - data.get('timestamp', 0) > 3600:  # 1 hour
                cache_file.unlink()  # Remove expired cache
                return None
            return data
        except:
            return None

    def set(self, url: str, content: Dict[str, Any]):
        """Cache content"""
        cache_key = self._get_cache_key(url)
        cache_file = self.cache_dir / f"{cache_key}.json"

        data = {
            'url': url,
            'timestamp': time.time(),
            'content': content
        }

        cache_file.write_text(json.dumps(data, indent=2))


class WebResearchAgent(Agent):
    """AI agent with controlled web access for research and documentation"""

    def __init__(self, context: Dict[str, Any]):
        super().__init__(context)

        # Web research configuration
        self.web_config = {
            'allowed_domains': [
                'docs.npmjs.com',      # NPM documentation
                'reactjs.org',         # React docs
                'laravel.com',         # Laravel docs
                'flutter.dev',         # Flutter docs
                'developer.mozilla.org', # MDN Web Docs
                'stackoverflow.com',   # Programming Q&A
                'github.com',          # GitHub repositories
                'pypi.org',            # Python packages
                'pub.dev',             # Dart/Flutter packages
                'nodejs.org',          # Node.js docs
                'webpack.js.org',      # Webpack docs
                'vitejs.dev',          # Vite docs
                'tailwindcss.com',     # Tailwind CSS
                'getbootstrap.com'     # Bootstrap
            ],
            'request_timeout': 10,
            'max_content_length': 50000,
            'requests_per_minute': 10
        }

        self.web_client = SafeWebClient(self.web_config)
        self.cache = DocumentationCache(Path.home() / ".sanaa" / "web_cache")

        # Research capabilities
        self.capabilities = {
            'documentation_lookup': self._lookup_documentation,
            'package_info': self._get_package_info,
            'api_reference': self._get_api_reference,
            'best_practices': self._get_best_practices,
            'troubleshooting': self._get_troubleshooting_info
        }

    async def _lookup_documentation(self, query: str, framework: str) -> str:
        """Look up documentation for specific framework/query"""
        urls = self._get_documentation_urls(query, framework)

        results = []
        for url in urls[:3]:  # Limit to 3 URLs
            result = await self._fetch_and_process(url)
            if result:
                results.append(result)

        if not results:
            return "No documentation found for the specified query."

        # Combine and summarize results
        combined_content = "\n\n".join(results)
        return await self._summarize_content(combined_content, query)

    async def _get_package_info(self, package_name: str, ecosystem: str) -> str:
        """Get package information from package registries"""
        if ecosystem.lower() == 'npm':
            url = f"https://registry.npmjs.org/{package_name}"
        elif ecosystem.lower() == 'pypi':
            url = f"https://pypi.org/pypi/{package_name}/json"
        elif ecosystem.lower() == 'pub':
            url = f"https://pub.dev/packages/{package_name}"
        else:
            return f"Unsupported package ecosystem: {ecosystem}"

        result = await self._fetch_and_process(url)
        if not result:
            return f"Package '{package_name}' not found in {ecosystem} registry."

        return self._format_package_info(result, ecosystem)

    async def _get_api_reference(self, api_name: str, framework: str) -> str:
        """Get API reference documentation"""
        urls = self._get_api_reference_urls(api_name, framework)

        results = []
        for url in urls[:2]:  # Limit to 2 URLs
            result = await self._fetch_and_process(url)
            if result:
                results.append(result)

        if not results:
            return f"No API reference found for '{api_name}' in {framework}."

        return "\n\n".join(results)

    async def _get_best_practices(self, topic: str, framework: str) -> str:
        """Get best practices for specific topics"""
        urls = self._get_best_practices_urls(topic, framework)

        results = []
        for url in urls[:3]:
            result = await self._fetch_and_process(url)
            if result:
                results.append(result)

        if not results:
            return f"No best practices found for '{topic}' in {framework}."

        return await self._extract_best_practices(results, topic)

    async def _get_troubleshooting_info(self, error_message: str, framework: str) -> str:
        """Get troubleshooting information for errors"""
        # Search Stack Overflow and documentation
        urls = self._get_troubleshooting_urls(error_message, framework)

        results = []
        for url in urls[:3]:
            result = await self._fetch_and_process(url)
            if result:
                results.append(result)

        if not results:
            return f"No troubleshooting information found for the specified error."

        return await self._extract_solutions(results, error_message)

    def _get_documentation_urls(self, query: str, framework: str) -> List[str]:
        """Generate documentation URLs based on query and framework"""
        base_urls = {
            'react': 'https://reactjs.org/docs/',
            'laravel': 'https://laravel.com/docs/',
            'flutter': 'https://flutter.dev/docs/',
            'vue': 'https://vuejs.org/guide/',
            'angular': 'https://angular.io/docs/',
            'nodejs': 'https://nodejs.org/docs/',
            'python': 'https://docs.python.org/3/',
            'django': 'https://docs.djangoproject.com/',
            'fastapi': 'https://fastapi.tiangolo.com/',
            'typescript': 'https://www.typescriptlang.org/docs/',
            'javascript': 'https://developer.mozilla.org/docs/Web/JavaScript'
        }

        urls = []
        if framework in base_urls:
            urls.append(f"{base_urls[framework]}{query.replace(' ', '-').lower()}")

        # Add general documentation search
        urls.append(f"https://developer.mozilla.org/search?q={urllib.parse.quote(query)}")

        return urls

    def _get_api_reference_urls(self, api_name: str, framework: str) -> List[str]:
        """Generate API reference URLs"""
        urls = []

        if framework == 'react':
            urls.extend([
                f"https://reactjs.org/docs/react-api.html#{api_name}",
                f"https://github.com/facebook/react/blob/main/packages/react/src/{api_name}.js"
            ])
        elif framework == 'laravel':
            urls.extend([
                f"https://laravel.com/api/10.x/Illuminate/{api_name}.html",
                f"https://laravel.com/docs/api/{api_name}"
            ])
        elif framework == 'flutter':
            urls.extend([
                f"https://api.flutter.dev/flutter/{api_name.replace('.', '/')}.html",
                f"https://flutter.dev/docs/reference/api/{api_name}"
            ])

        return urls

    def _get_best_practices_urls(self, topic: str, framework: str) -> List[str]:
        """Generate best practices URLs"""
        urls = []

        # Framework-specific best practices
        if framework == 'react':
            urls.extend([
                "https://reactjs.org/docs/thinking-in-react.html",
                "https://github.com/airbnb/javascript/tree/master/react"
            ])
        elif framework == 'laravel':
            urls.extend([
                "https://laravel.com/docs/artisan",
                "https://github.com/alexeymezenin/laravel-best-practices"
            ])

        # General best practices
        urls.extend([
            f"https://stackoverflow.com/search?q={urllib.parse.quote(f'{framework} {topic} best practices')}",
            f"https://github.com/search?q={urllib.parse.quote(f'{framework} {topic} best practices')}"
        ])

        return urls

    def _get_troubleshooting_urls(self, error_message: str, framework: str) -> List[str]:
        """Generate troubleshooting URLs"""
        urls = []

        # Stack Overflow search
        query = f"{framework} {error_message}"
        urls.append(f"https://stackoverflow.com/search?q={urllib.parse.quote(query)}")

        # Framework-specific troubleshooting
        if framework == 'react':
            urls.append("https://reactjs.org/docs/error-boundaries.html")
        elif framework == 'laravel':
            urls.append("https://laravel.com/docs/errors")

        return urls

    async def _fetch_and_process(self, url: str) -> Optional[str]:
        """Fetch and process web content"""
        # Check cache first
        cached = self.cache.get(url)
        if cached:
            return cached['content']

        # Fetch from web
        result = await self.web_client.safe_get(url)

        if result and 'error' not in result:
            content = self._extract_relevant_content(result['content'], result['content_type'])
            if content:
                # Cache the result
                self.cache.set(url, content)
                return content

        return None

    def _extract_relevant_content(self, content: str, content_type: str) -> Optional[str]:
        """Extract relevant content from web response"""
        if content_type == 'application/json':
            try:
                data = json.loads(content)
                # Extract useful information from JSON responses
                if 'description' in data:
                    return data['description']
                elif 'readme' in data:
                    return data['readme']
                elif 'content' in data:
                    return data['content']
            except:
                pass
        else:
            # Extract text content from HTML
            # Remove scripts, styles, and navigation
            content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
            content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL)
            content = re.sub(r'<nav[^>]*>.*?</nav>', '', content, flags=re.DOTALL)
            content = re.sub(r'<header[^>]*>.*?</header>', '', content, flags=re.DOTALL)
            content = re.sub(r'<footer[^>]*>.*?</footer>', '', content, flags=re.DOTALL)

            # Extract text from paragraphs and headings
            text_parts = []
            for match in re.finditer(r'<(h[1-6]|p)[^>]*>(.*?)</\1>', content, re.IGNORECASE):
                text = re.sub(r'<[^>]+>', '', match.group(2)).strip()
                if text and len(text) > 20:  # Skip very short content
                    text_parts.append(text)

            if text_parts:
                return '\n\n'.join(text_parts[:10])  # Limit to first 10 relevant sections

        return None

    async def _summarize_content(self, content: str, query: str) -> str:
        """Use LLM to summarize web content"""
        summary_prompt = f"""
        Please summarize the following web content in relation to the query: "{query}"

        Content:
        {content[:2000]}  # Limit content length

        Provide a concise, relevant summary focusing on information related to the query.
        """

        # Use the base LLM integration
        return await self._generate_response(summary_prompt, "You are a helpful assistant summarizing web content.")

    def _format_package_info(self, content: str, ecosystem: str) -> str:
        """Format package information"""
        try:
            if ecosystem == 'npm':
                data = json.loads(content)
                return f"""
Package: {data.get('name', 'Unknown')}
Version: {data.get('version', 'Unknown')}
Description: {data.get('description', 'No description')}
Homepage: {data.get('homepage', 'N/A')}
Repository: {data.get('repository', {}).get('url', 'N/A')}
"""
            elif ecosystem == 'pypi':
                data = json.loads(content)
                info = data.get('info', {})
                return f"""
Package: {info.get('name', 'Unknown')}
Version: {info.get('version', 'Unknown')}
Description: {info.get('summary', 'No description')}
Homepage: {info.get('home_page', 'N/A')}
Author: {info.get('author', 'N/A')}
"""
        except:
            return f"Could not parse package information from {ecosystem}."

        return content

    async def _extract_best_practices(self, results: List[str], topic: str) -> str:
        """Extract best practices from search results"""
        combined = "\n\n".join(results)

        prompt = f"""
        Extract and summarize the best practices related to "{topic}" from the following content:

        {combined[:3000]}

        Focus on actionable recommendations and common patterns.
        """

        return await self._generate_response(prompt, "You are an expert summarizing best practices.")

    async def _extract_solutions(self, results: List[str], error_message: str) -> str:
        """Extract solutions from troubleshooting content"""
        combined = "\n\n".join(results)

        prompt = f"""
        Analyze the following content and extract solutions for this error: "{error_message}"

        Content:
        {combined[:3000]}

        Provide specific, actionable solutions in order of relevance.
        """

        return await self._generate_response(prompt, "You are an expert troubleshooting technical issues.")

    async def _generate_response(self, user_query: str, context: str = "") -> str:
        """Generate response using LLM (inherited from base Agent)"""
        # This method should be implemented in the base Agent class
        # For now, return a placeholder
        return f"Web research completed for: {user_query}"