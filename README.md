# Focus Cat 🐈

A little animated pixel-art cat that lives on your Windows desktop. It wanders wherever it likes, naps, grooms, pounces on toys you give it, and hops up happily when you click it.

But if you open YouTube Shorts (or TikTok, or Reels) and start doomscrolling, it notices. It walks over to wherever your mouse is, puffs up, and yells at you with a countdown. If you're still scrolling five minutes later, it closes the tab.

![the cat's moods](docs/preview.png)

## How it works

There are two small pieces:

1. **The cat** (`FocusCat.exe`): a transparent, always-on-top window. Clicks go straight through the empty space around it, and clicking the cat itself doesn't steal focus from what you're doing.
2. **The Firefox extension** (`extension/`): every 2 seconds it tells the cat which tab you're looking at, and closes that tab when the cat says so. It only ever talks to `127.0.0.1` on your own PC, so nothing gets sent anywhere.

The timeline when you land on a doomscroll page:

| time on the page | what the cat does |
| --- | --- |
| 0 to 15 s | side-eyes you: "hm?" (this is so one accidental click doesn't set it off) |
| after 15 s | comes over and gets mad, with a 5:00 countdown that gets more dramatic as it goes |
| 5 min later | closes the tab and looks smug about it |

Some details:

- Leave the page and the cat calms down right away and tells you it's proud of you. The countdown only *pauses*, though. You need to stay away for 90 seconds before it fully resets, so quickly flicking to another tab and back won't work.
- If you go right back after it closes a tab, you get 60 seconds, not another five minutes.
- It only counts time when Firefox is the window you're actually using. Shorts open in the background is fine.

## Setup

### 1. Get the cat running

**Easiest option:** download [`FocusCat.exe`](../../releases/latest/download/FocusCat.exe) from the [latest release](../../releases/latest). The extension is there too, as `focus-cat-link.xpi`. Windows will probably say "Windows protected your PC" the first time because the exe isn't code-signed. Click **More info**, then **Run anyway**.

**Or run it from source:** install Python 3.10+ from python.org (keep "tcl/tk" ticked, it is by default), then double-click `FocusCat.pyw`. No other packages are needed.

**Or build the exe yourself:** run `build.bat`. It puts the exe in `dist\FocusCat.exe`.

Once it's running, right-click the cat and tick **Start with Windows** so it's always there.

### 2. Install the Firefox extension

Regular Firefox only keeps extensions installed permanently if Mozilla has signed them. Signing your own copy is free and takes a few minutes:

1. Zip up the *contents* of the `extension` folder (select `manifest.json`, `background.js` and `icon.svg`, then right-click, **Send to**, **Compressed (zipped) folder**). Or use the `.xpi` from the latest release.
2. Go to <https://addons.mozilla.org/developers/addon/submit/distribution>, sign in, and pick **On your own**. This keeps it private; it won't be listed publicly.
3. Upload the zip. Once it passes the automatic checks (usually a few minutes), download the signed `.xpi`.
4. Drag the signed `.xpi` into a Firefox window and click **Add**.

**Just want to try it first?** Open `about:debugging#/runtime/this-firefox`, click **Load Temporary Add-on…** and pick `extension/manifest.json`. This works right away but disappears when Firefox restarts.

To make it work in private windows too, go to `about:addons`, click Focus Cat Link, and set **Run in Private Windows** to Allow.

### 3. Check it's connected

Right-click the cat. The top line should say "Mochi can see Firefox ✓". Then choose **Show me the angry cat (demo)** to watch the angry routine without actually opening Shorts.

## Things you can do with the cat

- **Click it** to pet it (hearts and purring). It won't accept pets while it's mad at you.
- **Drag it** somewhere and let go. Drop it on its bed and it'll stay there.
- **Give it toys** (right-click the cat, **Give a toy**): a yarn ball, a toy mouse, or a scratching post. It plays with them on its own. Drag a toy next to it, or throw one (drag and let go mid-motion), and it'll chase it right away.
- **Give it a bed** (right-click, **Give a bed**): a cardboard box or a cushion. While there's a bed out, the cat lives in it: it sits in the box or naps on the cushion instead of wandering into your way, and only pops out to play now and then. It still comes out to yell at you if you doomscroll. Right-click the bed and put it away to let the cat roam again.
- **Feed it** (right-click, **Feed**): a treat, which it runs over and gobbles (sometimes followed by a sugar rush), or a food bowl. Every so often it gets hungry and goes to eat from the bowl, which then stays empty until you click it to fill it up again.
- **Laser pointer** (right-click, **Laser pointer**): a red dot rides along with your mouse and the cat chases it all over the screen, pouncing when it gets close. Clicks go straight through the dot, so you can keep working. It gets tired after a while, flops down panting, then goes again. Turn it off from the same menu.
- Every now and then it gets **the zoomies** and sprints around the screen for no reason.
- Toys, beds and bowls can be dragged anywhere, stay where you left them next time, and go away with a right-click.
- **Right-click** for the menu:
  - take a 15 min break (it naps and ignores Shorts until the break is over)
  - demo mode
  - start with Windows
  - settings (how the cat looks, plus the doomscroll rules)
  - quit

## Settings

Right-click the cat, then **Settings…**. The window has a live preview of your cat.

- **Look:** pick a quick preset (Ginger, Tabby, Tuxedo, Calico and more) or choose your own fur colour, a second colour for two-tone cats (as a bib, socks or patches), inner ear and eye colours, ear shape (pointy, round, folded), eye shape (content, dots, big & shiny), style (animated, pixel, minimal or outlined), extras (stripes, blush, whiskers) and size. The animated cat's art is fixed, so ear shape, eye shape and extras only apply to the other styles.
- **Doomscroll rules:** the grace period, how long until the tab gets closed, break length, and which sites count.

Everything is saved to `%APPDATA%\FocusCat\config.json`. You can also edit that file directly (restart the cat afterwards). The ones the window doesn't cover:

| setting | default | what it does |
| --- | --- | --- |
| `forgive_after_seconds` | 90 | how long you have to stay away before the countdown resets |
| `second_chance_seconds` | 60 | countdown if you go right back after a close |
| `port` | 47321 | local port. If you change it, also change it in `extension/manifest.json` and `background.js` (needs a restart) |

## Development

```
python -m unittest discover -s tests     # logic + server tests
python -m focuscat --selftest            # opens the cat, runs every animation and the close flow, exits
python tools/render_sprites.py out.png   # renders the animated cat's behaviours to a PNG (needs Pillow)
python tools/render_poses.py out.png     # same for the drawn styles
python tools/build_sprites.py            # re-pack the sprite sheet after editing it
```

The code:

- `focuscat/watcher.py` has the doomscroll timing rules and no UI code.
- `focuscat/sprites.py` draws the animated cat. Its frames come from `assets/cat_template.aseprite`, packed into `focuscat/sprite_data.py` by `tools/build_sprites.py`, and get recoloured to your look.
- `focuscat/pixel.py` has the simpler hand-made pixel cat as little text grids.
- `focuscat/drawing.py` draws the other two styles and picks the right one.
- `focuscat/app.py` has the window, the behaviour, and the mouse handling.
- `focuscat/settings_window.py` is the Settings window.
- `focuscat/items.py` has the toys and beds (pixel art and their little windows).
- `focuscat/server.py` is the local endpoint the extension talks to.

Errors get logged to `%APPDATA%\FocusCat\focuscat.log`.
