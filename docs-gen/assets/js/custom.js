// Put your custom JS code here

// Fix search index URL for GitHub Pages
(function() {
  // Override fetch to fix search-index.json URL
  const originalFetch = window.fetch;
  window.fetch = function(url, options) {
    if (typeof url === 'string' && url === '/search-index.json') {
      // Get the base URL from the current location
      const baseUrl = window.location.pathname.split('/').slice(0, -1).join('/');
      url = baseUrl + '/search-index.json';
    }
    return originalFetch.call(this, url, options);
  };
})();
