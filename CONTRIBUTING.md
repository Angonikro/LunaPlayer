# Contributing to LunaPlayer

Thank you for helping improve LunaPlayer.

## Before submitting changes

- Keep changes focused and avoid unrelated playback changes.
- Run ` /usr/bin/python3 -m compileall -q app ui main.py gtk_app.py `.
- Run `/usr/bin/python3 -m unittest discover -s tests -v`.
- For packaging changes, run `bash packaging/build-deb.sh` on a Debian-based system with `dpkg-deb` installed.
- Do not claim DVD/Blu-ray hardware testing unless it was performed on a real drive and disc.

Please include the operating system, desktop session, reproduction steps, and relevant terminal output in bug reports.
