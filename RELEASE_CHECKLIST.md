# Before public release

- Confirm project name and ownership, replace copyright placeholder, and approve the MIT license.
- Run the CI workflow; download and launch the actual AppImage on the intended Linux desktop.
- Verify MKV playback, audio, seeking, fullscreen, descriptions, shuffle, original order, and thumbnails with and without system FFmpeg.
- Test a large real archive; test rescanning while thumbnails generate and reconnecting a drive. Never use your only copy for destructive tests.
- Check that the archive remains unchanged, and that closing works during scanning and thumbnail generation.
- Test on at least one other distribution/desktop if claiming portability. Record versions and known issues.
- Review binary redistribution obligations for Qt, Python, PyInstaller and bundled transitive libraries, provide notices and source/relinking information as applicable. Do not publish the binary before this review.
- Add your own actual screenshots (the conversation screenshots may contain personal viewing history).
- Publish a prerelease with the AppImage and checksum; mark v1.0 only after verification.
