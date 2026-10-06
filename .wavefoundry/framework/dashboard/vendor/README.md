# Vendored dashboard scripts

The dashboard loads these third-party scripts from its own origin, so it needs no network
access and no CDN. Each file was taken unmodified from the package tarball published on the
npm registry (`npm pack <name>@<version>`, which checks the tarball against the registry's
published integrity). Do not edit them; to update one, repeat the `npm pack`, replace the
file and its licence, and update the version and SHA-256 in the file table and the tarball URL
and integrity in the registry table below.

| File | Package | Source in the tarball | Licence | SHA-256 |
| --- | --- | --- | --- | --- |
| `react/react.production.min.js` | `react@18.3.1` | `package/umd/react.production.min.js` | MIT (`react/LICENSE`) | `d949f1c3687aedadcedac85261865f29b17cd273997e7f6b2bfc53b2f9d4c4dd` |
| `react-dom/react-dom.production.min.js` | `react-dom@18.3.1` | `package/umd/react-dom.production.min.js` | MIT (`react-dom/LICENSE`) | `35f4f974f4b2bcd44da73963347f8952e341f83909e4498227d4e26b98f66f0d` |
| `elkjs/elk.bundled.js` | `elkjs@0.10.0` | `package/lib/elk.bundled.js` | EPL-2.0 (`elkjs/LICENSE.md`) | `48d338d5aeddd9503ccf1d12661c11b5d7d43c6afc5f66c7ddb2ea4170c0f6bf` |

Licence texts are copied from the same tarballs: `react/LICENSE` and `react-dom/LICENSE`
(MIT; the `@license` headers in the minified files are kept) and `elkjs/LICENSE.md`
(Eclipse Public License 2.0).

## Registry integrity

Each package's tarball URL and the registry's `dist.integrity` for it (SHA-512, in the base64
form npm prints). The integrity belongs to the tarball; the SHA-256 values above belong to the
files extracted from it.

| Package | Tarball | `dist.integrity` |
| --- | --- | --- |
| `react@18.3.1` | `https://registry.npmjs.org/react/-/react-18.3.1.tgz` | `sha512-wS+hAgJShR0KhEvPJArfuPVN1+Hz1t0Y6n5jLrGQbkb4urgPE/0Rve+1kMB1v/oWgHgm4WIcV+i7F2pTVj+2iQ==` |
| `react-dom@18.3.1` | `https://registry.npmjs.org/react-dom/-/react-dom-18.3.1.tgz` | `sha512-5m4nQKp+rZRb09LNH59GM4BxTh9251/ylbKIbpe7TpGxfJ+9kv6BLkLBXIjjspbgbnIBNqlI23tRnTWT0snUIw==` |
| `elkjs@0.10.0` | `https://registry.npmjs.org/elkjs/-/elkjs-0.10.0.tgz` | `sha512-v/3r+3Bl2NMrWmVoRTMBtHtWvRISTix/s9EfnsfEWApNrsmNjqgqJOispCGg46BPwIFdkag3N/HYSxJczvCm6w==` |

## Reproduce and check

In the Wavefoundry source repository, one command runs the whole check:
`python3 .wavefoundry/framework/scripts/verify_vendored_scripts.py` (on Windows, `py -3` in
place of `python3`). It downloads each tarball in the registry table from
`https://registry.npmjs.org/` only, compares its SHA-512 with the recorded `dist.integrity`,
reads the recorded source file from the tarball in memory, and compares its SHA-256 and bytes
with the vendored file and the file table. It exits 0 when every check passes, 1 when any check
fails (even when another package could not be checked), and 2 when the check could not be made
and nothing failed (this README cannot be parsed, or a download failed or was refused). Each
table is found by its exact header line, and every row must match the table's format; a
malformed row, an indented row, a row missing its leading pipe, or a row after a blank
line inside a table stops the check
(exit 2, naming the line) rather than being skipped. Every
redirect target is checked before it is followed, so a host off the registry is never
contacted. A deliberate refusal (a non-registry URL, a redirect that left the registry, a
tarball over the size cap) prints `refused:`; a download that could not complete prints
`download failed:`.
`python3 .wavefoundry/framework/scripts/verify_vendored_scripts.py --offline` makes no network
request: it hashes each vendored file and compares it with the file table, exiting 0 when every
file matches, 1 when a file differs or is missing (each is named) and 2 when this README cannot
be parsed. The default test suite and `build_pack` run the same offline comparison, so a
changed vendored file stops a build.
The online check uses the network, so it is optional and never part of the default test suite;
it is development-only and is not included in the framework distribution, so a target repository
does not have it and uses the manual procedure below.

Run these in an empty scratch folder, once per package. The example uses `react@18.3.1`;
substitute the package, version, source path and vendored path from the tables above.

With npm (macOS, Linux, WSL2 and Windows):

```sh
npm pack react@18.3.1 --json
tar -xzf react-18.3.1.tgz
mkdir react
cp package/umd/react.production.min.js react/react.production.min.js
cp package/LICENSE react/LICENSE
openssl dgst -sha256 react/react.production.min.js
```

`npm pack` checks the download against the registry's `dist.integrity`, and the `integrity`
field in its JSON output must equal the registry table. The copied file's SHA-256 must equal
the file table, and the copied file and licence must be byte-identical to the vendored ones
(`cmp react/LICENSE <this folder>/react/LICENSE`). Each tarball unpacks into `package/`;
remove it between packages. The elkjs licence is `package/LICENSE.md`. In PowerShell, `mkdir`
and `cp` work as written; check the SHA-256 with the `Get-FileHash` form below.

Without npm, download the tarball and compare its SHA-512 in base64 with the registry table.
On macOS, Linux and WSL2 (`openssl base64 -A` keeps the value on one line; plain `base64`
wraps at 76 characters on GNU systems):

```sh
curl -fsSLO https://registry.npmjs.org/react/-/react-18.3.1.tgz
openssl dgst -sha512 -binary react-18.3.1.tgz | openssl base64 -A
```

On Windows 10 1803 and later, with the `curl.exe` and `tar.exe` that ship with Windows, in
PowerShell (`Resolve-Path` is needed because `ReadAllBytes` resolves a relative name against
the process folder, not the PowerShell location):

```powershell
curl.exe -fsSLO https://registry.npmjs.org/react/-/react-18.3.1.tgz
[Convert]::ToBase64String([Security.Cryptography.SHA512]::Create().ComputeHash([IO.File]::ReadAllBytes((Resolve-Path "react-18.3.1.tgz").ProviderPath)))
tar.exe -xzf react-18.3.1.tgz
(Get-FileHash "package/umd/react.production.min.js" -Algorithm SHA256).Hash.ToLower()
```

Prefix the printed value with `sha512-` to compare it with the registry table, then extract
the tarball and check each file's SHA-256 as above (comparing `Get-FileHash` values also stands
in for `cmp`, which PowerShell lacks).

## elkjs source

elkjs is distributed under the Eclipse Public License 2.0. Its source code is available at
<https://github.com/kieler/elkjs>, tag `0.10.0`; the layout algorithms it compiles are from the
Eclipse Layout Kernel at <https://github.com/eclipse/elk>. The file here is the unmodified
compiled bundle from the npm package.
