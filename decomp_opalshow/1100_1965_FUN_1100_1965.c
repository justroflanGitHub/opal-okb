
byte __cdecl16near FUN_1100_1965(void)

{
  byte bVar1;
  byte in_BL;
  byte *unaff_SI;
  int unaff_DI;
  undefined2 unaff_ES;
  
  out(0x3ce,7);
  bVar1 = 0xaa;
  if (((uint)unaff_SI & 1) == 0) {
    bVar1 = 0x55;
  }
  out(0x3cf,bVar1);
  if ((*unaff_SI & in_BL) == in_BL) {
    for (; unaff_DI != 0; unaff_DI = unaff_DI + -1) {
      unaff_SI = unaff_SI + 1;
      bVar1 = bVar1 >> 1 | bVar1 << 7;
      out(0x3cf,bVar1);
      if (*unaff_SI != 0xff) {
        return bVar1;
      }
    }
    bVar1 = bVar1 >> 1 | bVar1 << 7;
    out(0x3cf,bVar1);
  }
  return bVar1;
}

