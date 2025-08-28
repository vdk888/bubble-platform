const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = function(app) {
  // Use localhost for local development, backend for Docker
  const backendUrl = process.env.DOCKER_ENV === 'true' ? 'http://backend:8000' : 'http://localhost:8000';
  
  console.log('🔧 Setting up explicit proxy for /api ->', backendUrl);
  console.log('🔧 This will override any package.json proxy setting for /api paths');
  console.log('🔧 DOCKER_ENV:', process.env.DOCKER_ENV);
  
  app.use(
    '/api',
    createProxyMiddleware({
      target: backendUrl,
      changeOrigin: true,
      logLevel: 'debug',
      secure: false,
      followRedirects: false,
      headers: {
        'Host': 'localhost:3000'  // Force correct host header
      },
      onProxyReq: (proxyReq, req, res) => {
        console.log('🔧 Proxying request:', req.method, req.url, '->', backendUrl + req.url);
        console.log('🔧 Proxy headers:', proxyReq.getHeaders());
      },
      onProxyRes: (proxyRes, req, res) => {
        console.log('🔧 Proxy response:', proxyRes.statusCode, req.url);
      },
      onError: (err, req, res) => {
        console.error('🚨 Proxy error:', err.message);
        console.error('🚨 Target URL was:', backendUrl);
        res.writeHead(500, { 'Content-Type': 'text/plain' });
        res.end('Proxy error: ' + err.message);
      }
    })
  );
};