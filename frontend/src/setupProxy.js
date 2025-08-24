const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = function(app) {
  console.log('🔧 Setting up explicit proxy for /api -> http://backend:8000');
  console.log('🔧 This will override any package.json proxy setting for /api paths');
  app.use(
    '/api',
    createProxyMiddleware({
      target: 'http://backend:8000',
      changeOrigin: true,
      logLevel: 'debug',
      secure: false,
      followRedirects: false,
      headers: {
        'Host': 'localhost:3000'  // Force correct host header
      },
      onProxyReq: (proxyReq, req, res) => {
        console.log('🔧 Proxying request:', req.method, req.url, '-> http://backend:8000' + req.url);
        console.log('🔧 Proxy headers:', proxyReq.getHeaders());
      },
      onProxyRes: (proxyRes, req, res) => {
        console.log('🔧 Proxy response:', proxyRes.statusCode, req.url);
      },
      onError: (err, req, res) => {
        console.error('🚨 Proxy error:', err.message);
        res.writeHead(500, { 'Content-Type': 'text/plain' });
        res.end('Proxy error: ' + err.message);
      }
    })
  );
};