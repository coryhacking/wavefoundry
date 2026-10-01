# Vendored dashboard scripts

The dashboard loads these third-party scripts from its own origin, so it needs no network
access and no CDN. Each file was taken unmodified from the package tarball published on the
npm registry (`npm pack <name>@<version>`, which checks the tarball against the registry's
published integrity). Do not edit them; to update one, repeat the `npm pack`, replace the
file and its licence, and update the version and hash below.

| File | Package | Source in the tarball | Licence | SHA-256 |
| --- | --- | --- | --- | --- |
| `react/react.production.min.js` | `react@18.3.1` | `package/umd/react.production.min.js` | MIT (`react/LICENSE`) | `d949f1c3687aedadcedac85261865f29b17cd273997e7f6b2bfc53b2f9d4c4dd` |
| `react-dom/react-dom.production.min.js` | `react-dom@18.3.1` | `package/umd/react-dom.production.min.js` | MIT (`react-dom/LICENSE`) | `35f4f974f4b2bcd44da73963347f8952e341f83909e4498227d4e26b98f66f0d` |
| `elkjs/elk.bundled.js` | `elkjs@0.10.0` | `package/lib/elk.bundled.js` | EPL-2.0 (`elkjs/LICENSE.md`) | `48d338d5aeddd9503ccf1d12661c11b5d7d43c6afc5f66c7ddb2ea4170c0f6bf` |

Licence texts are copied from the same tarballs: `react/LICENSE` and `react-dom/LICENSE`
(MIT; the `@license` headers in the minified files are kept) and `elkjs/LICENSE.md`
(Eclipse Public License 2.0).

## elkjs source

elkjs is distributed under the Eclipse Public License 2.0. Its source code is available at
<https://github.com/kieler/elkjs>, tag `0.10.0`; the layout algorithms it compiles are from the
Eclipse Layout Kernel at <https://github.com/eclipse/elk>. The file here is the unmodified
compiled bundle from the npm package.
