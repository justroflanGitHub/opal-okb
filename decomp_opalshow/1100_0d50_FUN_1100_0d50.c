
void __cdecl16near FUN_1100_0d50(void)

{
  undefined2 in_CX;
  undefined2 uVar1;
  byte extraout_DL;
  undefined2 extraout_DX;
  undefined2 extraout_DX_00;
  int in_BX;
  int unaff_BP;
  undefined2 unaff_DS;
  undefined1 in_CF;
  int iVar2;
  
  FUN_1100_0da6();
  if (!(bool)in_CF) {
    FUN_1100_0e16();
    LOCK();
    uVar1 = *(undefined2 *)0x10c6;
    *(undefined2 *)0x10c6 = in_CX;
    UNLOCK();
    LOCK();
    *(undefined2 *)0x10c8 = extraout_DX;
    UNLOCK();
    FUN_1100_0e16();
    FUN_1100_0e54();
    if ((bool)in_CF) {
      LOCK();
      *(undefined2 *)0x10c8 = extraout_DX_00;
      UNLOCK();
    }
    in_BX = in_BX + 1;
    iVar2 = in_BX;
    FUN_1100_0e49(in_BX);
    if ((bool)in_CF) {
      LOCK();
      *(undefined2 *)0x10c6 = uVar1;
      UNLOCK();
    }
    *(byte *)0x10e2 = extraout_DL & 7;
    (*(code *)*(undefined2 *)0x30c)(in_BX + 1);
    do {
      (*(code *)*(undefined2 *)0x330)(iVar2);
      iVar2 = 0x1d91;
      (*(code *)*(undefined2 *)0x316)();
      *(char *)0x10e2 = *(char *)0x10e2 + '\x01';
      *(byte *)0x10e2 = *(byte *)0x10e2 & 7;
      unaff_BP = unaff_BP + -1;
    } while (unaff_BP != 0);
  }
  *(undefined2 *)0x10d2 = 0xffff;
  return;
}

