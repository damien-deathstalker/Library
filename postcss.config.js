/* Build config for src/css/app.css -> shelf/static/shelf/css/app.css
 *
 * Two builds, chosen by NODE_ENV, which the npm scripts set through
 * postcss-cli's `--env`:
 *
 *   build    cssnano runs. This is the file Django serves and the only one
 *            committed for PythonAnywhere, so it is the one that goes over
 *            the wire.
 *   develop  no cssnano. The output stays readable while you work on it, and
 *            the comments in src/ are worth more than the kilobytes during
 *            the five minutes it takes to find the rule you just broke.
 *
 * Minifying is the default rather than the exception, so that a stray `npx
 * postcss` cannot quietly produce an unminified file for someone to commit.
 * The way to get the readable one is to ask for it.
 *
 * Two things that used to go wrong here, both worth knowing about:
 *
 * `--minify` is not a postcss-cli 11 flag. It is not rejected either -- it is
 * simply ignored, so `npm run build` read as though it minified while the
 * shipped stylesheet stayed the full 65 KB, comments and all. `--env` is the
 * flag that exists. (`--config` is gone in the same release, for the same
 * reason, which is why the choice lives in this file and not in a second one.)
 *
 * And the plugin options are read from NODE_ENV directly rather than through
 * postcss-load-config's `ctx` argument: postcss 8 passes a function's return
 * value through as options, so a function returning `false` here was read as
 * "call cssnano with a function as its options", and the stylesheet came out
 * minified either way. NODE_ENV cannot be got wrong like that.
 */
const MINIFY_EXCEPT = process.env.NODE_ENV === 'develop';

module.exports = {
	plugins: {
		'postcss-import': {},
		autoprefixer: {},
		cssnano: MINIFY_EXCEPT ? false : { preset: 'default' },
	},
};
