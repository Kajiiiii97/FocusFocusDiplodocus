# Assets

`cat_template.aseprite` is the cat sprite sheet (64×64 cells, one animation per row) that the
animated cat is built from. It was supplied by the repo owner from a third-party pixel-art pack,
so check that pack's license before redistributing it.

After editing it, regenerate the packed data the app uses:

```
python tools/build_sprites.py
```
