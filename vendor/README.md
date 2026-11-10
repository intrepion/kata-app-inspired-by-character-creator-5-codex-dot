# Vendored renderer

Three.js **0.180.0** from the official `three` npm package (MIT).
Package SHA-512 integrity: `sha512-o+qycAMZrh+TsE01GqWUxUIKR1AL0S8pq7zDkYOQw8GqfX8b8VoCKYUoHbhiX5j+7hr8XsuHDVU6+gkQJQKg9w==`.

Only the minified ES module/core, GLTFLoader, GLTFExporter, BufferGeometryUtils and MIT license are retained. Addon imports of `three` are rewritten to the local `../three.module.min.js` module. No CDN or runtime network request is needed.

Source: https://github.com/mrdoob/three.js/tree/r180
License: [THREE-LICENSE.txt](THREE-LICENSE.txt).
