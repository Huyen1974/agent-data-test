const http = require('http');
const port = parseInt(process.env.PORT) || 8080;
http.createServer((req, res) => {
  res.writeHead(200, {'Content-Type': 'text/plain'});
  res.end('Hello, World!');
}).listen(port, () => {
  console.log(`listening on port ${port}`);
});
