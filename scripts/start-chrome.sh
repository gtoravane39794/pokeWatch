#!/usr/bin/env bash
# Starts a dedicated Chrome window PokeWatch uses to read Target (looks like a normal browser to Target).
# Leave it open (minimizing is fine). It uses its own profile, so your normal Chrome is untouched.
set -e
PROFILE="$HOME/.pokewatch-chrome"
mkdir -p "$PROFILE"
if curl -s -m 2 http://127.0.0.1:9222/json/version >/dev/null; then echo "Chrome debug window already running."; exit 0; fi
case "$(uname)" in
  Darwin) open -na "Google Chrome" --args --remote-debugging-port=9222 --user-data-dir="$PROFILE" --no-first-run --no-default-browser-check "https://www.target.com/" ;;
  *) (google-chrome --remote-debugging-port=9222 --user-data-dir="$PROFILE" --no-first-run "https://www.target.com/" >/dev/null 2>&1 &) ;;
esac
echo "Started. Keep that window open."
