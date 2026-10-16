
byte __cdecl16near FUN_1100_2eff(void)

{
  byte in_AL;
  byte in_AH;
  byte in_CH;
  byte bVar1;
  bool bVar2;
  
  bVar1 = in_CH;
  do {
    if ((in_AL & in_CH) != 0) break;
    bVar1 = bVar1 | in_CH;
    if ((in_AH & bVar1) != 0) {
      return in_AL;
    }
    bVar2 = (bool)(in_CH & 1);
    in_CH = in_CH >> 1 | in_CH << 7;
  } while (!bVar2);
  return ~in_AL;
}

