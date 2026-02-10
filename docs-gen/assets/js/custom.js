// Put your custom JS code here

// Fix search index URL for GitHub Pages
(function() {
  // Override fetch to fix search-index.json URL
  const originalFetch = window.fetch.bind(window);
  window.fetch = function(url, options) {
    if (typeof url === 'string' && url === '/search-index.json') {
      const origin = window.location.origin;
      const primaryUrl = origin + '/search-index.json';
      const pathSegments = window.location.pathname.split('/').filter(Boolean);
      const baseSegment = pathSegments.length > 0 ? pathSegments[0] : '';
      const fallbackUrl = baseSegment
        ? origin + '/' + baseSegment + '/search-index.json'
        : primaryUrl;

      return originalFetch(primaryUrl, options).then((response) => {
        if (response && response.ok) {
          return response;
        }
        if (fallbackUrl === primaryUrl) {
          return response;
        }
        return originalFetch(fallbackUrl, options);
      });
    }
    return originalFetch(url, options);
  };
})();
