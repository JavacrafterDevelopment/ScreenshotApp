Made this app cause I had to use screenburst before, Didn't realize it had a built in screenshot limit, lost a lot of stuff, also its in a terrible ps1 file, exe wouldve been better. It also used an outdated BMP format which wastes so much space. This app has BMP if needed but not recommended.

Best feature alongside the automatic screenshots is to have a custom hotkey to screenshot with and it will give u a notification that it took, it rememvers the numbering from the automatic screenshots too so it is easy to find when sorting through screenshots. It also includes the word MANUAL so you know that you manually took that screenshot.

will eventually add ability to remove the MANUAL from the name of the files where you took the screenshot manually and possibly some other things


Will also add a native MACOS app too based on the Swift Coding language.


## Releases

Push a version tag and [the Release workflow](.github/workflows/release.yml) does
the rest:

```bash
# set version.txt, e.g. to 0.0.2, then:
git commit -am "Release 0.0.2"
git tag v0.0.2
git push origin main v0.0.2
```

It builds the portable folder with `build.py`, packs it as
`ScreenshotApp-windows-x64.zip` with a manifest of every file's SHA-256
(`tools/release-package.ps1`), publishes the release, and writes `update.json` to
the `updates` branch (`tools/publish-update.ps1`). The
[Javacrafter Launcher](https://github.com/JavacrafterDevelopment/Launcher) reads
that file to offer the update and checks every file against it before installing.
