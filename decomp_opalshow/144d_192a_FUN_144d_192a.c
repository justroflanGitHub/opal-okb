
undefined2 __cdecl16near FUN_144d_192a(void)

{
  int in_CX;
  uint uVar1;
  uint uVar2;
  uint unaff_SI;
  int unaff_DI;
  undefined2 unaff_ES;
  undefined2 unaff_DS;
  bool bVar3;
  undefined4 uVar4;
  
  if ((*(uint *)(unaff_DI + -2) & 1) != 0) {
    in_CX = (in_CX - *(uint *)(unaff_DI + -2)) + -1;
  }
  uVar1 = in_CX + 2;
  uVar2 = 0x7fff;
  do {
    if (uVar2 <= *(uint *)0x5b4) break;
    uVar2 = uVar2 >> 1;
  } while (uVar2 != 0);
  do {
    if (CARRY2(uVar1,unaff_SI)) {
      return 0;
    }
    if (!CARRY2(uVar1 + unaff_SI,uVar2)) {
      bVar3 = (uVar1 + unaff_SI + uVar2 & ~uVar2) == unaff_SI;
      uVar4 = FUN_144d_1964();
      if (!bVar3) {
        return (int)uVar4;
      }
      uVar2 = ~(uint)((ulong)uVar4 >> 0x10);
    }
    uVar2 = uVar2 >> 1;
  } while (uVar2 != 0);
  return 0;
}

