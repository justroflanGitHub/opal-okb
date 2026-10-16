
undefined4 __cdecl16near FUN_1100_2e8d(void)

{
  byte bVar1;
  undefined2 in_DX;
  int iVar2;
  undefined1 *unaff_DI;
  undefined2 unaff_ES;
  undefined2 unaff_DS;
  bool bVar3;
  
  out(0x3c4,2);
  bVar1 = 8;
  iVar2 = 3;
  do {
    out(0x3c5,bVar1);
    *unaff_DI = *(undefined1 *)(iVar2 + 0x1160);
    iVar2 = iVar2 + -1;
    bVar3 = (bool)(bVar1 & 1);
    bVar1 = bVar1 >> 1;
  } while (!bVar3);
  out(0x3c4,2);
  out(0x3c5,0xf);
  return CONCAT22(in_DX,0x20f);
}

