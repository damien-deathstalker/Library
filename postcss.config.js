/* Build config for src/css/app.css -> shelf/static/shelf/css/app.css
 *
 * --minify (used by `npm run build`) pulls in cssnano through postcss-cli.
 * `npm run expand` omits it so the compiled output stays readable while you
 * work on it.
 */
module.exports = {
  plugins: [
    require('postcss-import')(),
    require('autoprefixer'),
  ],
};