
undefined2 __cdecl16near FUN_1100_2744(void)

{
  byte bVar1;
  undefined2 in_AX;
  byte bVar2;
  byte in_CH;
  byte in_DL;
  byte in_DH;
  byte in_BL;
  
  bVar2 = (byte)((uint)in_AX >> 8);
  bVar1 = 0;
  if (((in_BL ^ in_DL) & in_CH) != 0) {
    bVar1 = (in_BL ^ in_DH) & in_CH & bVar2;
  }
  return CONCAT11(bVar2,bVar1);
}

