#!/bin/bash
# Probe keys against OPALSHOW splash; stop when screen changes.
cd "$(dirname "$0")/.."
BASE="size=517x348 nonblack=44859 distinct=93"
i=0
for KEY in SPACE ESC TAB A S D F G H J K L Q W E R T Y U I O P Z X C V B N M 0 1 2 3 4 5 6 7 8 9 F1 F2 F3 F4 F5 F6 F7 F8 F9 F10 PGDN HOME END DEL; do
  i=$((i+1))
  py -X utf8 scripts/dosbox_real.py "$KEY" > /dev/null 2>&1
  sleep 2.5
  powershell -NoProfile -File scripts/win_shot.ps1 > /dev/null 2>&1
  STAT=$(powershell -NoProfile -File scripts/_scratch_pngstat.ps1 "C:\\Users\\mikhail\\AppData\\Local\\Temp\\dosbox_win.png" 2>/dev/null | tail -1)
  if [ "$STAT" != "$BASE" ]; then
    cp "C:/Users/mikhail/AppData/Local/Temp/dosbox_win.png" "capture/opcom_keyhit_${KEY}.png"
    echo "CHANGED on $KEY -> $STAT"
    exit 0
  fi
  echo "$i $KEY: same"
done
echo "NO KEY CHANGED SCREEN"
