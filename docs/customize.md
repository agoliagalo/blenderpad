# Customizing the keymap

The keymap lives in [`boards/shields/blenderpad/blenderpad.keymap`](../boards/shields/blenderpad/blenderpad.keymap). A blank template is available in [`template.keymap`](template.keymap).

## Rules

- Each layer contains exactly **18 keys**, in this order:

```
S1   S2   S3   S4
S5   S6   S7   S8
S9   S10  S11  S12
S13  S14  S15  S16  S17  S18
```

- The first layer is layer **0** (active at startup), the next one is layer **1**.

| Code | Effect |
|---|---|
| `&kp G` | G key |
| `&kp LS(A)` | Shift + A (`LC` = Ctrl, `LA` = Alt) |
| `&kp LC(LS(Z))` | Ctrl + Shift + Z |
| `&kp KP_N7` | numpad 7 (Blender viewport views) |
| `&kp KP_DOT` | numpad dot |
| `&kp TAB`, `&kp RET`, `&kp ESC`, `&kp DEL` | Tab, Enter, Escape, Delete |
| `&kp LSHFT`, `&kp LCTRL`, `&kp LALT` | modifiers on their own |
| `&tog 1` | toggles layer 1 on and off |
| `&mo 1` | layer 1 while the key is held |
| `&trans` | uses the key from the layer below |
| `&none` | does nothing |
| `&bootloader` | puts the keyboard in flash mode |

On layer 1, put `&trans` at the position of your `&tog 1`, otherwise you can't get back out.

Place `&bootloader` somewhere you won't hit by accident: pressing it makes the keyboard stop responding until you unplug it or flash it.

## Pitfalls

**AZERTY.** ZMK sends QWERTY key positions. With a French AZERTY layout on the computer: `&kp Q` types A, `&kp W` types Z, `&kp SEMI` types M (and the other way around for A and Z). Other letters and the numpad are unaffected.

**Num Lock.** `KP_N...` keys only type numbers when Num Lock is on. Otherwise they act as Home, End, arrows...

## Applying your changes

1. Edit `blenderpad.keymap`, then `git add .`, `git commit -m "..."`, `git push`.
2. On GitHub, **Actions** tab: wait for the green build, download the firmware under **Artifacts**.
3. Enter flash mode: press your `&bootloader` key, or short `RST` to `GND` twice quickly.
4. Drag the `.uf2` file onto the `NICENANO` drive that appears.
