
undefined4 __cdecl16near FUN_144d_1964(void)

{
  undefined2 in_DX;
  int in_BX;
  int unaff_SI;
  int iVar1;
  int unaff_DI;
  undefined2 unaff_DS;
  undefined1 in_ZF;
  undefined4 uVar2;
  
  uVar2 = FUN_144d_1986();
  iVar1 = (int)uVar2;
  if (!(bool)in_ZF) {
    iVar1 = (int)uVar2 + (int)((ulong)uVar2 >> 0x10);
    *(undefined2 *)(iVar1 + -2) = 0xfffe;
    *(int *)(in_BX + 6) = iVar1;
    *(int *)(unaff_SI + -2) = (iVar1 - unaff_SI) + -1;
    iVar1 = unaff_DI;
  }
  return CONCAT22(in_DX,iVar1);
}

