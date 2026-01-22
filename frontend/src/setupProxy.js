const proxy = require('http-proxy-middleware');
// Handle different versions of http-proxy-middleware
const createProxyMiddleware = proxy.createProxyMiddleware || proxy;

module.exports = function (app) {
    // Docker environment (Server) will provide BACKEND_URL.
    // Local environment (npm start) will default to localhost.
    const target = process.env.BACKEND_URL || 'http://127.0.0.1:8000';

    console.log(`[Proxy] Setting up proxy to: ${target}`);

    app.use(
        ['/api', '/health', '/docs', '/openapi.json'],
        createProxyMiddleware({
            target: target,
            changeOrigin: true,
            pathRewrite: {
                // If backend expects /api prefix, keep it. 
                // Our backend uses /api, so no rewrite needed usually, 
                // but let's Ensure we pass it through correctly.
            },
            onError: (err, req, res) => {
                console.error('[Proxy] Error:', err);
            }
        })
    );
};
